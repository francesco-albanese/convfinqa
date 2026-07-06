"""Behavioral tests for the SendMessageUseCase agent loop."""

import json
import uuid
from typing import Any, cast

import pytest

from convfinqa.application.agent.iteration import ITERATION_CAP
from convfinqa.application.agent.stream_events import Finish, StreamEvent, ToolResult
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.domain.ports.llm import LLMChunk
from convfinqa.domain.value_objects import StopReason
from tests.unit.agent_loop_fakes import (
    StubLLM as _StubLLM,
)
from tests.unit.agent_loop_fakes import (
    make_use_case as _make_use_case,
)

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


async def _collect_stream(
    use_case: SendMessageUseCase, user_id: uuid.UUID
) -> list[StreamEvent]:
    events: list[StreamEvent] = []
    async for event in use_case.stream(
        user_id=user_id,
        conversation_id="conv-1",
        user_text="How did revenue change in the pinned document?",
    ):
        events.append(event)
    return events


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
    assert stub.call_count == ITERATION_CAP


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
    assert json.loads(tool_results[0].result) == {"error": "tool call blocked"}


@pytest.mark.asyncio
async def test_blocked_tool_call_does_not_stream_raw_args() -> None:
    """Policy-blocked tool inputs stay out of stream events."""
    unsafe_sql = "SELECT value_num FROM cells; SELECT value_num FROM cells"
    tool_chunks = _tool_use_chunk("c1", "sql_query", {"sql": unsafe_sql})
    stub = _StubLLM(responses=[tool_chunks, _text_chunks("done")])
    uc = _make_use_case(stub)

    events = await _collect_stream(uc, uuid.uuid4())

    assert unsafe_sql not in repr(events)
    tool_results = [e for e in events if isinstance(e, ToolResult)]
    assert len(tool_results) == 1
    assert json.loads(tool_results[0].result) == {"error": "tool call blocked"}


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
    assert stub.call_count == 2
    second_call_messages = stub.received_wire_messages[1]
    assistant_msgs = [m for m in second_call_messages if m.get("role") == "assistant"]
    assert assistant_msgs, "assistant message must be in second-call wire"
    content = assistant_msgs[0].get("content")
    assert isinstance(content, list), (
        "Anthropic format: content must be a list of blocks"
    )
    blocks = cast("list[dict[str, Any]]", content)
    block_types = [b.get("type") for b in blocks]
    assert "thinking" in block_types, "thinking block must be replayed"
    thinking_blocks = [b for b in blocks if b.get("type") == "thinking"]
    assert thinking_blocks[0].get("signature") == thinking_sig
