"""Behavioral tests for the SendMessageUseCase agent loop."""

import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from convfinqa.application.agent.tools import Tool
from convfinqa.application.agent.tools.math import MathInput, MathOutput
from convfinqa.application.use_cases.send_message import (
    ITERATION_CAP,
    TOOL_TIMEOUT_MATH_S,
    Finish,
    ToolResult,
    _execute_tool,  # noqa: PLC2701
)
from convfinqa.domain.ports.llm import LLMChunk
from convfinqa.domain.value_objects import StopReason

# ---------------------------------------------------------------------------
# Stub LLM helpers
# ---------------------------------------------------------------------------


def _tool_use_chunk(call_id: str, name: str, args: dict[str, str]) -> list[LLMChunk]:
    args_str = json.dumps(args)
    return [
        LLMChunk(tool_call_event="start", tool_call_id=call_id, tool_call_name=name),
        LLMChunk(
            tool_call_event="delta", tool_call_id=call_id, tool_call_delta=args_str
        ),
        LLMChunk(tool_call_event="complete", tool_call_id=call_id, tool_call_name=name),
        LLMChunk(finish_reason_tool_use=True),
    ]


def _text_chunks(text: str) -> list[LLMChunk]:
    return [LLMChunk(text=text)]


class _StubLLM:
    """Replays a sequence of chunk lists, one per LLM call."""

    def __init__(self, responses: list[list[LLMChunk]]) -> None:
        self._responses = list(responses)
        self._call_count = 0
        self.received_wire_messages: list[list[dict[str, Any]]] = []

    async def stream(
        self,
        messages: Any,
        system: str,
        tools: Any = None,
        generation_name: str | None = None,
        trace_user_id: str | None = None,
        session_id: str | None = None,
        environment: str | None = None,
    ) -> AsyncIterator[LLMChunk]:
        self.received_wire_messages.append(list(messages))
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        for chunk in self._responses[idx]:
            yield chunk


# ---------------------------------------------------------------------------
# Minimal stub for ConversationRepository, DocumentRepository, lock
# ---------------------------------------------------------------------------


@dataclass
class _FakeMessage:
    id: str
    conversation_id: str
    role: Any
    content: str
    created_at: datetime
    stop_reason: Any = None
    parts: Any = None
    reasoning_signatures: Any = None


@dataclass
class _FakeConversation:
    id: str = "conv-1"
    user_id: str = "user-1"
    document_id: str = "doc-1"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    messages: tuple = field(default_factory=tuple)


@dataclass
class _FakeDocument:
    id: str = "doc-1"
    ticker: str | None = "JKHY"
    year: int | None = 2009
    page: int | None = None
    title: str | None = "Test Doc"
    pre_text: str | None = ""
    post_text: str | None = ""
    table_data: Any = None
    column_order: Any = None


class _FakeConversationRepo:
    def __init__(self) -> None:
        self.conv = _FakeConversation()
        self.appended: list[Any] = []

    async def get(self, conversation_id: str, user_id: Any) -> _FakeConversation:
        return self.conv

    async def create(self, user_id: Any, document_id: str) -> _FakeConversation:
        return self.conv

    async def append_message(self, conversation_id: str, message: Any) -> None:
        self.appended.append(message)


class _FakeDocumentRepo:
    async def get(self, document_id: str) -> _FakeDocument:
        return _FakeDocument()


class _FakeLock:
    """Always acquires the lock."""

    def try_acquire(self, conversation_id: str) -> Any:
        return self

    async def __aenter__(self) -> bool:
        return True

    async def __aexit__(self, *_: Any) -> None:
        pass


class _RecordedSpan:
    def __init__(self, call: dict[str, Any]) -> None:
        self._call = call

    def set_output(self, output: str) -> None:
        self._call["output"] = output

    def set_error(self) -> None:
        self._call["level"] = "error"


class _RecordingObservability:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @asynccontextmanager
    async def start_as_current_observation(
        self, as_type: str, name: str, input: dict[str, Any] | None = None
    ) -> AsyncIterator[_RecordedSpan]:
        call = {"as_type": as_type, "name": name, "input": input}
        self.calls.append(call)
        yield _RecordedSpan(call)

    def propagate_attributes(
        self,
        user_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        pass

    def update_current_generation(self, **kwargs: Any) -> None:
        pass

    async def flush(self) -> None:
        pass


async def _collect_stream(use_case: Any, user_id: uuid.UUID) -> list[Any]:
    events = []
    async for event in use_case.stream(
        user_id=user_id,
        conversation_id="conv-1",
        user_text="hello",
    ):
        events.append(event)
    return events


def _make_use_case(llm: Any) -> Any:
    from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
    from convfinqa.application.use_cases.send_message import SendMessageUseCase

    return SendMessageUseCase(
        llm=llm,
        conversations=_FakeConversationRepo(),  # type: ignore[arg-type]
        documents=_FakeDocumentRepo(),  # type: ignore[arg-type]
        locks=_FakeLock(),  # type: ignore[arg-type]
        system_prompt_framing="You are a helpful assistant.",
        observability=NoOpLangfuseClient(),  # type: ignore[arg-type]
        llm_model="test-model",
        environment="test",
    )


# ---------------------------------------------------------------------------
# Test: iteration cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_iteration_cap_stops_loop() -> None:
    """Agent loop emits ITERATION_CAP stop reason after 10 tool-use responses."""
    # The LLM always returns a tool call → the loop must cap at ITERATION_CAP
    always_tool = _tool_use_chunk("c1", "subtract", {"a": "1", "b": "0"})
    stub = _StubLLM(responses=[always_tool] * (ITERATION_CAP + 5))
    uc = _make_use_case(stub)

    events = await _collect_stream(uc, uuid.uuid4())

    finish_events = [e for e in events if isinstance(e, Finish)]
    assert len(finish_events) == 1
    assert finish_events[0].stop_reason == StopReason.ITERATION_CAP
    assert stub._call_count == ITERATION_CAP


# ---------------------------------------------------------------------------
# Test: unknown tool name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_tool_name_returns_error_result() -> None:
    """Tool call to an unregistered name returns ToolResult(is_error=True)."""
    tool_chunks = _tool_use_chunk("c1", "nonexistent_tool", {"a": "1", "b": "2"})
    # Second call returns text so the loop ends
    text_resp = _text_chunks("done")
    stub = _StubLLM(responses=[tool_chunks, text_resp])
    uc = _make_use_case(stub)

    events = await _collect_stream(uc, uuid.uuid4())

    tool_results = [e for e in events if isinstance(e, ToolResult)]
    assert len(tool_results) == 1
    assert tool_results[0].is_error is True
    assert "unknown tool" in tool_results[0].result


# ---------------------------------------------------------------------------
# Test: tool timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_timeout_returns_error() -> None:
    """_execute_tool returns is_error=True when the tool exceeds the timeout."""
    import time

    def blocking_callable(**_: Any) -> dict[str, Any]:
        time.sleep(TOOL_TIMEOUT_MATH_S * 5)  # 5x the timeout → guaranteed timeout
        return {"result": "never reached"}

    slow_tool = Tool(
        name="subtract",
        description="slow",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=blocking_callable,
        doc_md="",
    )

    from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient

    result_json, is_error = await _execute_tool(
        slow_tool,
        '{"a": "1", "b": "2"}',
        NoOpLangfuseClient(),  # type: ignore[arg-type]
    )

    assert is_error is True
    data = json.loads(result_json)
    assert "timeout" in data["error"] or "failed" in data["error"]


@pytest.mark.asyncio
async def test_execute_tool_records_tool_span_output() -> None:
    """Successful tool execution records a tool observation with args and output."""
    tool = Tool(
        name="add",
        description="add",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=lambda **kwargs: {"result": int(kwargs["a"]) + int(kwargs["b"])},
        doc_md="",
    )
    observability = _RecordingObservability()

    result_json, is_error = await _execute_tool(
        tool,
        '{"a": "2", "b": "3"}',
        observability,  # type: ignore[arg-type]
    )

    assert is_error is False
    assert json.loads(result_json) == {"result": 5}
    assert observability.calls == [
        {
            "as_type": "tool",
            "name": "add",
            "input": {"a": "2", "b": "3"},
            "output": result_json,
        }
    ]


@pytest.mark.asyncio
async def test_execute_tool_records_error_level_on_invalid_args() -> None:
    """Invalid tool args record an errored tool observation and return an error."""
    tool = Tool(
        name="add",
        description="add",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=lambda **kwargs: {"result": int(kwargs["a"]) + int(kwargs["b"])},
        doc_md="",
    )
    observability = _RecordingObservability()

    result_json, is_error = await _execute_tool(
        tool,
        '{"a": "2"}',
        observability,  # type: ignore[arg-type]
    )

    assert is_error is True
    assert "error" in json.loads(result_json)
    assert observability.calls[0]["as_type"] == "tool"
    assert observability.calls[0]["name"] == "add"
    assert observability.calls[0]["level"] == "error"
    assert observability.calls[0]["output"] == result_json


# ---------------------------------------------------------------------------
# Test: thinking-block signature replay in wire messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_thinking_blocks_included_in_wire_for_second_iteration() -> None:
    """When Anthropic returns a thinking block + signature, the assistant message
    in the second-iteration wire includes the thinking block with its signature."""
    thinking_sig = "abc123signature"

    # First LLM call: thinking block + tool use
    first_response = [
        LLMChunk(reasoning_event="start", reasoning_block_id="blk1"),
        LLMChunk(
            reasoning_event="delta",
            reasoning_text="I need to subtract.",
            reasoning_block_id="blk1",
        ),
        LLMChunk(
            reasoning_event="end",
            reasoning_block_id="blk1",
            reasoning_signature=thinking_sig,
        ),
        *_tool_use_chunk("c2", "subtract", {"a": "206588", "b": "181001"}),
    ]
    # Second LLM call: final text
    second_response = _text_chunks("The answer is 25587.")

    stub = _StubLLM(responses=[first_response, second_response])
    uc = _make_use_case(stub)
    await _collect_stream(uc, uuid.uuid4())

    # The second LLM call's messages must include the thinking block
    assert stub._call_count == 2
    second_call_messages = stub.received_wire_messages[1]
    assistant_msgs = [m for m in second_call_messages if m.get("role") == "assistant"]
    assert assistant_msgs, "assistant message must be in second-call wire"
    content = assistant_msgs[0].get("content")
    assert isinstance(content, list), (
        "Anthropic format: content must be a list of blocks"
    )
    block_types = [b.get("type") for b in content]
    assert "thinking" in block_types, "thinking block must be replayed"
    thinking_blocks = [b for b in content if b.get("type") == "thinking"]
    assert thinking_blocks[0].get("signature") == thinking_sig
