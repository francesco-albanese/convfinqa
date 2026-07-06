import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from convfinqa.application.agent.sql.citation_extractor import extract_citations
from convfinqa.application.agent.stream_events import Citation, ToolResult
from convfinqa.application.agent.tool_executor import execute_tool
from convfinqa.application.agent.tool_policy_gate import (
    BLOCKED_TOOL_ERROR,
    ToolPolicyGate,
)
from convfinqa.application.agent.tools import TOOL_REGISTRY, build_sql_query_tool
from convfinqa.application.agent.wire import safe_json_loads
from convfinqa.domain.entities import Document
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.logging import get_logger

logger = get_logger("convfinqa.replay")
_tool_policy_gate = ToolPolicyGate()


async def execute_and_replay_tools(
    tool_calls: dict[str, dict[str, Any]],
    assistant_thinking_blocks: list[dict[str, Any]],
    parts_in_order: list[dict[str, Any]],
    wire_messages: list[dict[str, Any]],
    document: Document,
    seen_citations: set[tuple[str, str]],
    observability: ObservabilityPort,
) -> AsyncGenerator[ToolResult | Citation]:
    tool_use_blocks: list[dict[str, Any]] = []
    tool_results_for_wire: list[dict[str, Any]] = []

    for call_id, tc_state in tool_calls.items():
        raw_args = tc_state.get("args", "".join(tc_state["args_chunks"]))
        tool_name = tc_state["name"]
        policy_decision = _tool_policy_gate.decide(tool_name, raw_args)

        if policy_decision.blocked:
            async with observability.start_as_current_observation(
                as_type="tool", name=tool_name, input=safe_json_loads(raw_args)
            ) as span:
                result_str = json.dumps({"error": BLOCKED_TOOL_ERROR})
                span.set_output(result_str)
                span.set_error()
            is_error = True
        else:
            tool = TOOL_REGISTRY[tool_name]
            if tool.name == "sql_query":
                tool = build_sql_query_tool(document)
            result_str, is_error = await execute_tool(tool, raw_args, observability)

        yield ToolResult(call_id=call_id, result=result_str, is_error=is_error)

        parts_in_order.append(
            {
                "kind": "tool_call",
                "call_id": call_id,
                "name": tool_name,
                "args": raw_args,
            }
        )
        parts_in_order.append(
            {
                "kind": "tool_result",
                "call_id": call_id,
                "is_error": is_error,
                "result": result_str,
            }
        )

        if tool_name == "sql_query" and not is_error:
            try:
                result_data = json.loads(result_str)
                rows = result_data.get("rows", [])
            except (json.JSONDecodeError, AttributeError) as exc:
                logger.log(
                    logging.WARNING,
                    "sql_query_result_parse_error",
                    extra={
                        "exc_type": exc.__class__.__name__,
                        "exc_message": str(exc) or exc.__class__.__name__,
                        "call_id": call_id,
                    },
                )
                rows = []

            if rows:
                try:
                    sql = json.loads(raw_args).get("sql", "")
                except (json.JSONDecodeError, AttributeError):
                    sql = ""
                for row_label, col_label in extract_citations(sql):
                    pair = (row_label, col_label)
                    if pair in seen_citations:
                        continue
                    seen_citations.add(pair)
                    parts_in_order.append(
                        {
                            "kind": "citation",
                            "row_label": row_label,
                            "col_label": col_label,
                        }
                    )
                    yield Citation(row_label=row_label, col_label=col_label)

        tool_use_blocks.append(
            {
                "type": "tool_use",
                "id": call_id,
                "name": tool_name,
                "input": safe_json_loads(raw_args),
            }
        )
        tool_results_for_wire.append(
            {"role": "tool", "tool_call_id": call_id, "content": result_str}
        )

    if assistant_thinking_blocks:
        wire_messages.append(
            {
                "role": "assistant",
                "content": assistant_thinking_blocks + tool_use_blocks,
            }
        )
    else:
        wire_messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tb["id"],
                        "type": "function",
                        "function": {
                            "name": tb["name"],
                            "arguments": json.dumps(tb["input"]),
                        },
                    }
                    for tb in tool_use_blocks
                ],
            }
        )
    wire_messages.extend(tool_results_for_wire)
