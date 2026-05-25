"""Tests for Citation event behavior in execute_and_replay_tools."""

import json

import pytest

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.application.agent.replay import execute_and_replay_tools
from convfinqa.application.agent.stream_events import Citation, ToolResult
from convfinqa.domain.entities import Document


def _doc_with_table() -> Document:
    return Document(
        id="doc1",
        ticker="JKHY",
        year=2009,
        page=None,
        title="Test",
        pre_text=None,
        post_text=None,
        table_data={"Year ended June 30, 2009": {"net cash from operations": "206588"}},
        column_order=None,
    )


def _empty_doc() -> Document:
    return Document(
        id="doc1",
        ticker=None,
        year=None,
        page=None,
        title=None,
        pre_text=None,
        post_text=None,
        table_data=None,
        column_order=None,
    )


def _make_tool_call(call_id: str, name: str, args: dict) -> dict:
    raw = json.dumps(args)
    return {call_id: {"name": name, "args": raw, "args_chunks": [raw]}}


@pytest.mark.asyncio
async def test_sql_query_with_matching_rows_yields_citation() -> None:
    """sql_query that returns rows fires Citation events for each (row_label, col_label) pair."""
    sql = "SELECT value_num FROM cells WHERE row_label='net cash from operations' AND col_label='Year ended June 30, 2009'"
    tool_calls = _make_tool_call("c1", "sql_query", {"sql": sql})

    parts: list = []
    wire: list = []
    seen: set = set()

    events = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, _doc_with_table(), seen, NoOpLangfuseClient()
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
    tool_calls = _make_tool_call("c1", "sql_query", {"sql": sql})

    parts: list = []
    wire: list = []
    seen: set = set()

    events = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, _doc_with_table(), seen, NoOpLangfuseClient()
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

    parts: list = []
    wire: list = []
    seen: set = set()

    events = []
    async for event in execute_and_replay_tools(
        tool_calls, [], parts, wire, _doc_with_table(), seen, NoOpLangfuseClient()
    ):
        events.append(event)

    citations = [e for e in events if isinstance(e, Citation)]
    assert len(citations) == 1


@pytest.mark.asyncio
async def test_citation_part_added_to_parts_in_order() -> None:
    """When sql_query returns rows, a citation kind part is appended to parts_in_order."""
    sql = "SELECT value_num FROM cells WHERE row_label='net cash from operations' AND col_label='Year ended June 30, 2009'"
    tool_calls = _make_tool_call("c1", "sql_query", {"sql": sql})

    parts: list = []
    wire: list = []
    seen: set = set()

    async for _ in execute_and_replay_tools(
        tool_calls, [], parts, wire, _doc_with_table(), seen, NoOpLangfuseClient()
    ):
        pass

    citation_parts = [p for p in parts if p.get("kind") == "citation"]
    assert len(citation_parts) == 1
    assert citation_parts[0]["row_label"] == "net cash from operations"
    assert citation_parts[0]["col_label"] == "Year ended June 30, 2009"
