import pytest

from convfinqa.application.agent.replay import execute_and_replay_tools
from convfinqa.application.agent.stream_events import (
    StreamEvent,
    ToolCallArgsComplete,
    ToolCallStart,
    ToolResult,
)
from convfinqa.application.agent.tool_policy_gate import BLOCKED_TOOL_NAME
from tests.unit.replay_helpers import (
    MessageParts,
    RecordingObservability,
    SeenCitations,
    WireMessages,
    doc_with_table,
    make_tool_call,
)


@pytest.mark.asyncio
async def test_unknown_blocked_tool_call_omits_raw_name_and_args_from_sinks() -> None:
    raw_name = "evil_tool_name_system_prompt_SECRET"
    raw_secret = "AKIA1111111111111111"
    tool_calls = make_tool_call("c1", raw_name, {"sql": raw_secret})
    observability = RecordingObservability()

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    events: list[StreamEvent] = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, doc_with_table(), seen, observability
    ):
        events.append(event)

    serialized_sinks = repr(
        (events, parts, wire, observability.inputs, observability.names)
    )
    assert raw_name not in serialized_sinks
    assert raw_secret not in serialized_sinks
    assert parts[0]["name"] == BLOCKED_TOOL_NAME
    assert wire[0]["tool_calls"][0]["function"]["name"] == BLOCKED_TOOL_NAME
    assert observability.names == [BLOCKED_TOOL_NAME]


@pytest.mark.asyncio
async def test_blocked_tool_call_still_emits_start_and_args_before_result() -> None:
    """A blocked call must still open a tool part before closing it, or the
    AI SDK's UI message stream reducer throws (`No tool invocation found for
    tool call ID`) on the tool-output chunk and crashes the live chat stream.
    """
    tool_calls = make_tool_call("c1", "evil_tool", {"sql": "secret"})
    observability = RecordingObservability()

    events: list[StreamEvent] = []
    async for event in execute_and_replay_tools(
        tool_calls, [], [], [], doc_with_table(), set(), observability
    ):
        events.append(event)

    assert isinstance(events[0], ToolCallStart)
    assert events[0].call_id == "c1"
    assert events[0].name == BLOCKED_TOOL_NAME
    assert isinstance(events[1], ToolCallArgsComplete)
    assert events[1].call_id == "c1"
    assert isinstance(events[2], ToolResult)
    assert events[2].call_id == "c1"
    assert events[2].is_error is True
