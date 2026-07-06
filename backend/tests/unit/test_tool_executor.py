"""Tests for low-level tool execution behavior."""

import json
from typing import Any

import pytest

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.application.agent.tool_executor import TOOL_TIMEOUT_MATH_S, execute_tool
from convfinqa.application.agent.tools import Tool
from convfinqa.application.agent.tools.math import MathInput, MathOutput
from tests.unit.agent_loop_fakes import RecordingObservability


@pytest.mark.asyncio
async def test_execute_tool_timeout_returns_error() -> None:
    import time

    def blocking_callable(**_: Any) -> dict[str, Any]:
        time.sleep(TOOL_TIMEOUT_MATH_S * 5)
        return {"result": "never reached"}

    slow_tool = Tool(
        name="subtract",
        description="slow",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=blocking_callable,
        doc_md="",
    )

    result_json, is_error = await execute_tool(
        slow_tool,
        '{"a": "1", "b": "2"}',
        NoOpLangfuseClient(),  # type: ignore[arg-type]
    )

    assert is_error is True
    data = json.loads(result_json)
    assert "timeout" in data["error"] or "failed" in data["error"]


@pytest.mark.asyncio
async def test_execute_tool_records_tool_span_output() -> None:
    def add(a: str, b: str) -> dict[str, int]:
        return {"result": int(a) + int(b)}

    tool = Tool(
        name="add",
        description="add",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=add,
        doc_md="",
    )
    observability = RecordingObservability()

    result_json, is_error = await execute_tool(
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
    def add(a: str, b: str) -> dict[str, int]:
        return {"result": int(a) + int(b)}

    tool = Tool(
        name="add",
        description="add",
        input_schema=MathInput,
        output_schema=MathOutput,
        callable=add,
        doc_md="",
    )
    observability = RecordingObservability()

    result_json, is_error = await execute_tool(
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
