"""Tests for Citation event behavior in execute_and_replay_tools."""

import json

import pytest

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.application.agent.replay import execute_and_replay_tools
from convfinqa.application.agent.stream_events import Citation, StreamEvent, ToolResult
from convfinqa.application.agent.tool_policy_gate import (
    BLOCKED_TOOL_NAME,
    ToolPolicyReason,
)
from tests.unit.replay_helpers import (
    MessageParts,
    RecordingObservability,
    SeenCitations,
    WireMessages,
    doc_with_table,
    empty_doc,
    make_tool_call,
)


@pytest.mark.asyncio
async def test_sql_query_with_matching_rows_yields_citation() -> None:
    """sql_query that returns rows fires Citation events for each (row_label, col_label) pair."""
    sql = "SELECT value_num FROM cells WHERE row_label='net cash from operations' AND col_label='Year ended June 30, 2009'"
    tool_calls = make_tool_call("c1", "sql_query", {"sql": sql})

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    events: list[StreamEvent] = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, doc_with_table(), seen, NoOpLangfuseClient()
    ):
        events.append(event)

    citations = [e for e in events if isinstance(e, Citation)]
    assert len(citations) == 1
    assert citations[0].row_label == "net cash from operations"
    assert citations[0].col_label == "Year ended June 30, 2009"


@pytest.mark.asyncio
async def test_sql_query_with_zero_rows_yields_no_citation() -> None:
    """sql_query returning empty rows produces a ToolResult but NO Citation event."""
    sql = "SELECT value_num FROM cells WHERE row_label='nonexistent row' AND col_label='Year ended June 30, 2009'"
    tool_calls = make_tool_call("c1", "sql_query", {"sql": sql})

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    events: list[StreamEvent] = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, doc_with_table(), seen, NoOpLangfuseClient()
    ):
        events.append(event)

    tool_results = [e for e in events if isinstance(e, ToolResult)]
    citations = [e for e in events if isinstance(e, Citation)]

    assert len(tool_results) == 1
    assert tool_results[0].is_error is False
    assert len(citations) == 0


@pytest.mark.asyncio
async def test_duplicate_citations_within_turn_are_deduplicated() -> None:
    """The same (row_label, col_label) pair from two consecutive sql_query calls yields one Citation."""
    sql = "SELECT value_num FROM cells WHERE row_label='net cash from operations' AND col_label='Year ended June 30, 2009'"
    raw = json.dumps({"sql": sql})
    tool_calls = {
        "c1": {"name": "sql_query", "args": raw, "args_chunks": [raw]},
        "c2": {"name": "sql_query", "args": raw, "args_chunks": [raw]},
    }

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    events: list[StreamEvent] = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, doc_with_table(), seen, NoOpLangfuseClient()
    ):
        events.append(event)

    citations = [e for e in events if isinstance(e, Citation)]
    assert len(citations) == 1


@pytest.mark.asyncio
async def test_citation_part_added_to_parts_in_order() -> None:
    """When sql_query returns rows, a citation kind part is appended to parts_in_order."""
    sql = "SELECT value_num FROM cells WHERE row_label='net cash from operations' AND col_label='Year ended June 30, 2009'"
    tool_calls = make_tool_call("c1", "sql_query", {"sql": sql})

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    async for _ in execute_and_replay_tools(
        tool_calls, [], parts, wire, doc_with_table(), seen, NoOpLangfuseClient()
    ):
        pass

    citation_parts = [p for p in parts if p.get("kind") == "citation"]
    assert len(citation_parts) == 1
    assert citation_parts[0]["row_label"] == "net cash from operations"
    assert citation_parts[0]["col_label"] == "Year ended June 30, 2009"


@pytest.mark.asyncio
async def test_policy_blocked_sql_query_returns_sanitized_error() -> None:
    tool_calls = make_tool_call("c1", "sql_query", {"sql": "SELECT * FROM cells"})
    observability = RecordingObservability()

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    events: list[StreamEvent] = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, doc_with_table(), seen, observability
    ):
        events.append(event)

    tool_results = [e for e in events if isinstance(e, ToolResult)]
    assert len(tool_results) == 1
    assert tool_results[0].is_error is True
    assert json.loads(tool_results[0].result) == {"error": "tool call blocked"}
    assert "SELECT *" not in tool_results[0].result
    assert not [e for e in events if isinstance(e, Citation)]
    assert json.loads(parts[1]["result"]) == {"error": "tool call blocked"}
    assert observability.inputs == [
        {"blocked": True, "reason": ToolPolicyReason.UNSAFE_SQL}
    ]
    assert observability.names == [BLOCKED_TOOL_NAME]


@pytest.mark.asyncio
async def test_policy_blocked_tool_call_still_replays_to_wire_as_tool_result() -> None:
    tool_calls = make_tool_call(
        "c1",
        "sql_query",
        {"sql": "SELECT value_num FROM cells; SELECT value_num FROM cells"},
    )

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    async for _ in execute_and_replay_tools(
        tool_calls, [], parts, wire, doc_with_table(), seen, NoOpLangfuseClient()
    ):
        pass

    assert wire[-1] == {
        "role": "tool",
        "tool_call_id": "c1",
        "content": '{"error": "tool call blocked"}',
    }


@pytest.mark.asyncio
async def test_policy_allows_math_tool_execution() -> None:
    tool_calls = make_tool_call("c1", "subtract", {"a": "206588", "b": "181001"})

    parts: MessageParts = []
    wire: WireMessages = []
    seen: SeenCitations = set()

    events: list[StreamEvent] = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, empty_doc(), seen, NoOpLangfuseClient()
    ):
        events.append(event)

    tool_results = [e for e in events if isinstance(e, ToolResult)]
    assert len(tool_results) == 1
    assert tool_results[0].is_error is False
    assert json.loads(tool_results[0].result) == {"result": "25587"}
