import pytest

from convfinqa.application.agent.replay import execute_and_replay_tools
from convfinqa.application.agent.stream_events import StreamEvent
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
