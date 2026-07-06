from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any
from uuid import uuid4

from convfinqa.application.agent.iteration import IterationState
from convfinqa.application.agent.stream_events import (
    ReasoningDelta,
    ReasoningEnd,
    ReasoningStart,
    StreamEvent,
    TextDelta,
)
from convfinqa.application.output_guard import StreamingOutputGuard
from convfinqa.domain.ports.llm import LLMChunk


async def process_llm_chunks(
    chunks: AsyncIterable[LLMChunk],
    state: IterationState,
    parts_in_order: list[dict[str, Any]],
    text_chunks: list[str],
    current_text_buffer: list[str],
    reasoning_signatures: dict[str, str],
    assistant_thinking_blocks: list[dict[str, Any]],
    output_guard: StreamingOutputGuard | None = None,
) -> AsyncGenerator[StreamEvent]:
    guard = output_guard or StreamingOutputGuard()
    reasoning_guard: StreamingOutputGuard | None = None
    async for chunk in chunks:
        if chunk.reasoning_event == "start":
            if current_text_buffer:
                parts_in_order.append(
                    {"kind": "text", "content": "".join(current_text_buffer)}
                )
                current_text_buffer.clear()
            state.current_reasoning_id = (
                chunk.reasoning_block_id or f"rsn_{uuid4().hex}"
            )
            reasoning_guard = StreamingOutputGuard()
            yield ReasoningStart(id=state.current_reasoning_id)

        elif (
            chunk.reasoning_event == "delta" and state.current_reasoning_id is not None
        ):
            if reasoning_guard is None:
                reasoning_guard = StreamingOutputGuard()
            result = reasoning_guard.accept(chunk.reasoning_text)
            if result.blocked:
                blocked_id = state.current_reasoning_id
                state.reasoning_buffer = []
                state.current_reasoning_id = None
                reasoning_guard = None
                yield ReasoningEnd(id=blocked_id)
                refusal = guard.block()
                if refusal.text:
                    text_chunks.append(refusal.text)
                    current_text_buffer.append(refusal.text)
                    yield TextDelta(text=refusal.text)
                return
            if result.text:
                state.reasoning_buffer.append(result.text)
                yield ReasoningDelta(id=state.current_reasoning_id, text=result.text)

        elif chunk.reasoning_event == "end" and state.current_reasoning_id is not None:
            if reasoning_guard is not None:
                result = reasoning_guard.flush()
                if result.blocked:
                    blocked_id = state.current_reasoning_id
                    state.reasoning_buffer = []
                    state.current_reasoning_id = None
                    reasoning_guard = None
                    yield ReasoningEnd(id=blocked_id)
                    refusal = guard.block()
                    if refusal.text:
                        text_chunks.append(refusal.text)
                        current_text_buffer.append(refusal.text)
                        yield TextDelta(text=refusal.text)
                    return
                if result.text:
                    state.reasoning_buffer.append(result.text)
                    yield ReasoningDelta(
                        id=state.current_reasoning_id, text=result.text
                    )

            reasoning_text = "".join(state.reasoning_buffer)
            completed_id = state.current_reasoning_id
            sig = chunk.reasoning_signature

            if reasoning_text:
                parts_in_order.append(
                    {"kind": "reasoning", "id": completed_id, "content": reasoning_text}
                )
            if sig and chunk.reasoning_block_id:
                reasoning_signatures[chunk.reasoning_block_id] = sig
                assistant_thinking_blocks.append(
                    {"type": "thinking", "thinking": reasoning_text, "signature": sig}
                )

            state.reasoning_buffer = []
            state.current_reasoning_id = None
            reasoning_guard = None
            yield ReasoningEnd(id=completed_id)

        if chunk.text:
            result = guard.accept(chunk.text)
            if result.text:
                text_chunks.append(result.text)
                current_text_buffer.append(result.text)
                yield TextDelta(text=result.text)
            if result.blocked:
                return

        if chunk.tool_call_event == "start" and chunk.tool_call_id:
            state.tool_calls[chunk.tool_call_id] = {
                "name": chunk.tool_call_name or "",
                "args_chunks": [],
            }

        elif chunk.tool_call_event == "delta" and chunk.tool_call_id:
            if chunk.tool_call_id in state.tool_calls:
                state.tool_calls[chunk.tool_call_id]["args_chunks"].append(
                    chunk.tool_call_delta or ""
                )

        elif chunk.tool_call_event == "complete" and chunk.tool_call_id:
            if chunk.tool_call_id in state.tool_calls:
                args = "".join(state.tool_calls[chunk.tool_call_id]["args_chunks"])
                state.tool_calls[chunk.tool_call_id]["args"] = args

        if chunk.finish_reason_tool_use:
            state.finish_reason_tool_use = True

        if chunk.usage:
            state.usage = chunk.usage

    result = guard.flush()
    if result.text:
        text_chunks.append(result.text)
        current_text_buffer.append(result.text)
        yield TextDelta(text=result.text)
