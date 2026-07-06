from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from convfinqa.application.agent.chunks import process_llm_chunks
from convfinqa.application.agent.iteration import ITERATION_CAP, IterationState
from convfinqa.application.agent.replay import execute_and_replay_tools
from convfinqa.application.agent.stream_events import ReasoningEnd, StreamEvent
from convfinqa.application.output_guard import (
    OUTPUT_GUARD_REFUSAL,
    StreamingOutputGuard,
)
from convfinqa.application.security_signals import SecuritySignals
from convfinqa.domain.entities import Document
from convfinqa.domain.ports.llm import LLMPort, LLMToolSpec
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.domain.value_objects import StopReason, Usage


@dataclass(slots=True)
class AgentRunBuffers:
    wire_messages: list[dict[str, Any]]
    parts_in_order: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    text_chunks: list[str] = field(default_factory=list[str])
    current_text_buffer: list[str] = field(default_factory=list[str])
    reasoning_signatures: dict[str, str] = field(default_factory=dict[str, str])
    seen_citations: set[tuple[str, str]] = field(default_factory=set[tuple[str, str]])
    usage: Usage | None = None
    stop_reason: StopReason = StopReason.END_TURN
    output_blocked: bool = False

    @property
    def content(self) -> str:
        return "".join(self.text_chunks)

    def flush_current_text_part(self) -> None:
        if not self.current_text_buffer:
            return
        self.parts_in_order.append(
            {"kind": "text", "content": "".join(self.current_text_buffer)}
        )
        self.current_text_buffer.clear()

    def replace_visible_text(self, content: str) -> None:
        self.text_chunks[:] = [content]
        self.current_text_buffer[:] = [content]
        self.parts_in_order[:] = [
            part
            for part in self.parts_in_order
            if part.get("kind") not in {"text", "reasoning"}
        ]
        self.reasoning_signatures.clear()


async def stream_agent_iterations(
    *,
    llm: LLMPort,
    buffers: AgentRunBuffers,
    system_prompt: str,
    tool_specs: Sequence[LLMToolSpec],
    document: Document,
    observability: ObservabilityPort,
    user_id: UUID,
    conversation_id: str,
    environment: str,
    model: str,
    security_signals: SecuritySignals | None = None,
) -> AsyncGenerator[StreamEvent]:
    for iteration in range(ITERATION_CAP):
        state = IterationState()
        assistant_thinking_blocks: list[dict[str, Any]] = []
        output_guard = StreamingOutputGuard()

        async for event in process_llm_chunks(
            llm.stream(
                buffers.wire_messages,
                system_prompt,
                tool_specs,
                generation_name=f"iteration-{iteration}",
                trace_user_id=str(user_id),
                session_id=conversation_id,
                environment=environment,
                model=model,
            ),
            state,
            buffers.parts_in_order,
            buffers.text_chunks,
            buffers.current_text_buffer,
            buffers.reasoning_signatures,
            assistant_thinking_blocks,
            output_guard,
        ):
            yield event

        buffers.usage = state.usage
        if output_guard.blocked:
            buffers.output_blocked = True
            if security_signals is not None:
                security_signals.output_guard_blocked(
                    conversation_id=conversation_id,
                    document_id=document.id,
                    model=model,
                    reason=(
                        output_guard.reason.value
                        if output_guard.reason is not None
                        else "unknown"
                    ),
                )
            buffers.replace_visible_text(OUTPUT_GUARD_REFUSAL)
            break

        if state.current_reasoning_id:
            buffers.parts_in_order.append(
                {
                    "kind": "reasoning",
                    "id": state.current_reasoning_id,
                    "content": "".join(state.reasoning_buffer),
                }
            )
            yield ReasoningEnd(id=state.current_reasoning_id)

        buffers.flush_current_text_part()

        if not state.finish_reason_tool_use or not state.tool_calls:
            break

        if iteration == ITERATION_CAP - 1:
            buffers.stop_reason = StopReason.ITERATION_CAP
            if security_signals is not None:
                security_signals.cost_control_triggered(
                    conversation_id=conversation_id,
                    model=model,
                    control="iteration_cap",
                )
            break

        async for event in execute_and_replay_tools(
            state.tool_calls,
            assistant_thinking_blocks,
            buffers.parts_in_order,
            buffers.wire_messages,
            document,
            buffers.seen_citations,
            observability,
            security_signals=security_signals,
            conversation_id=conversation_id,
        ):
            yield event
