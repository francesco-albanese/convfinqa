"""Tests that internal error details never leak through the SSE boundary."""

import json

import pytest

from convfinqa.application.agent.sql.sql_query import sql_query
from convfinqa.application.agent.tools import Tool
from convfinqa.application.agent.tools.math import MathInput, MathOutput
from convfinqa.application.use_cases.send_message import (
    ToolResult,
    _execute_tool,  # noqa: PLC2701
)
from convfinqa.domain.entities import Document
from convfinqa.entrypoints.api.sse import to_ui_message_stream


def _make_exploding_tool(secret: str) -> Tool:
    def exploding(**_):  # type: ignore[return]
        raise RuntimeError(secret)

    return Tool(
        name="subtract",
        description="test tool",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=exploding,
        doc_md="",
    )


@pytest.mark.asyncio
async def test_tool_exception_returns_sanitized_message() -> None:
    """Unexpected tool exception produces a generic message, not internal details."""
    secret = "SECRET_FILE_PATH=/internal/secret"
    tool = _make_exploding_tool(secret)

    from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient

    result_json, is_error = await _execute_tool(
        tool, '{"a": "1", "b": "2"}', NoOpLangfuseClient()  # type: ignore[arg-type]
    )

    assert is_error is True
    result = json.loads(result_json)
    assert secret not in result.get("error", ""), "secret must not appear in error"
    assert result["error"] == "tool execution failed"


def _make_doc() -> Document:
    return Document(
        id="doc1",
        ticker=None,
        year=None,
        page=None,
        title=None,
        pre_text=None,
        post_text=None,
        table_data={"2009": {"revenue": "100"}},
        column_order=None,
    )


def test_sql_query_exception_returns_sanitized_message() -> None:
    """sqlite3 errors with file paths or internal details must not be exposed."""
    doc = _make_doc()
    with pytest.raises(ValueError) as exc_info:
        sql_query(doc, "SELECT * FROM nonexistent_table")
    assert "sql_query failed" in str(exc_info.value)
    assert "Traceback" not in str(exc_info.value)
    assert "File /" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_sse_sql_query_error_does_not_expose_sql_plan() -> None:
    """SSE output for a sql_query ToolResult error never exposes internal traces."""

    async def event_stream():  # type: ignore[return]
        yield ToolResult(
            call_id="c2",
            result='{"error":"sql_query failed"}',
            is_error=True,
        )

    frames: list[str] = []
    async for frame in to_ui_message_stream(event_stream()):  # type: ignore[arg-type]
        frames.append(frame)

    combined = "".join(frames)
    assert "Traceback" not in combined
    assert "File /" not in combined
    assert "tool-output-error" in combined


@pytest.mark.asyncio
async def test_sse_tool_error_does_not_expose_internal_detail() -> None:
    """SSE output for a tool error never contains internal stack trace markers."""

    async def event_stream():  # type: ignore[return]
        yield ToolResult(
            call_id="c1",
            result='{"error":"tool execution failed"}',
            is_error=True,
        )

    frames: list[str] = []
    async for frame in to_ui_message_stream(event_stream()):  # type: ignore[arg-type]
        frames.append(frame)

    combined = "".join(frames)
    assert "Traceback" not in combined
    assert "File /" not in combined
    assert "RuntimeError" not in combined
    assert "tool-output-error" in combined
