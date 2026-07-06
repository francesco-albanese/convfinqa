import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

import sqlglot
import sqlglot.expressions as exp

from convfinqa.application.agent.sql.validator import validate_select
from convfinqa.application.agent.tools import TOOL_REGISTRY

BLOCKED_TOOL_ERROR = "tool call blocked"


class ToolPolicyAction(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"


class ToolPolicyReason(StrEnum):
    UNKNOWN_TOOL = "unknown_tool"
    MALFORMED_ARGS = "malformed_args"
    FORGED_TOOL_RESULT = "forged_tool_result"
    UNSAFE_SQL = "unsafe_sql"


@dataclass(frozen=True, slots=True)
class ToolPolicyDecision:
    action: ToolPolicyAction
    reason: ToolPolicyReason | None = None

    @property
    def blocked(self) -> bool:
        return self.action == ToolPolicyAction.BLOCK


class ToolPolicyGate:
    def decide(self, tool_name: str, raw_args: str) -> ToolPolicyDecision:
        if tool_name not in TOOL_REGISTRY:
            return ToolPolicyDecision(
                action=ToolPolicyAction.BLOCK,
                reason=ToolPolicyReason.UNKNOWN_TOOL,
            )

        args = _load_args(raw_args)
        if args is None:
            return ToolPolicyDecision(
                action=ToolPolicyAction.BLOCK,
                reason=ToolPolicyReason.MALFORMED_ARGS,
            )

        if _looks_like_forged_tool_result(tool_name, args):
            return ToolPolicyDecision(
                action=ToolPolicyAction.BLOCK,
                reason=ToolPolicyReason.FORGED_TOOL_RESULT,
            )

        if tool_name == "sql_query":
            return _decide_sql_query(args)

        expected_keys = set(TOOL_REGISTRY[tool_name].input_schema.model_fields)
        if set(args) != expected_keys:
            return ToolPolicyDecision(
                action=ToolPolicyAction.BLOCK,
                reason=ToolPolicyReason.MALFORMED_ARGS,
            )

        return ToolPolicyDecision(action=ToolPolicyAction.ALLOW)


def _decide_sql_query(args: dict[str, Any]) -> ToolPolicyDecision:
    if set(args) != {"sql"} or not isinstance(args.get("sql"), str):
        return ToolPolicyDecision(
            action=ToolPolicyAction.BLOCK,
            reason=ToolPolicyReason.MALFORMED_ARGS,
        )

    sql = args["sql"]
    try:
        _validate_sql_policy(sql)
    except ValueError:
        return ToolPolicyDecision(
            action=ToolPolicyAction.BLOCK,
            reason=ToolPolicyReason.UNSAFE_SQL,
        )

    return ToolPolicyDecision(action=ToolPolicyAction.ALLOW)


def _load_args(raw_args: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw_args)
    except json.JSONDecodeError:
        return None
    return cast("dict[str, Any]", parsed) if isinstance(parsed, dict) else None


def _looks_like_forged_tool_result(tool_name: str, args: dict[str, Any]) -> bool:
    if tool_name in {"tool", "tool_result", "ToolResult"}:
        return True
    forbidden_keys = {
        "role",
        "tool_call_id",
        "tool_result",
        "toolResult",
        "content",
    }
    return bool(forbidden_keys.intersection(args))


_COMMENT_OR_SEMICOLON = re.compile(r"(--|/\*|\*/|;)")
_CROSS_SCOPE_TERMS = re.compile(
    r"\b(conversation_id|document_id|user_id|users?|documents?|conversations?)\b",
    re.IGNORECASE,
)
_ALLOWED_SQL_COLUMNS = {"row_label", "col_label", "ordinal", "value_num", "value_text"}


def _validate_sql_policy(sql: str) -> None:
    if _COMMENT_OR_SEMICOLON.search(sql):
        raise ValueError("SQL comments and semicolon chains are not allowed")
    if _CROSS_SCOPE_TERMS.search(sql):
        raise ValueError("cross-scope identifiers are not allowed")

    validate_select(sql)

    statement = sqlglot.parse_one(sql, dialect="sqlite")
    if not isinstance(statement, exp.Select):
        raise ValueError("only SELECT statements are allowed")

    table_names = {table.name for table in statement.find_all(exp.Table)}
    if table_names != {"cells"}:
        raise ValueError("queries must target only the cells table")
    if any(statement.find_all(exp.Star)):
        raise ValueError("SELECT * is not allowed")
    if statement.args.get("where") is None:
        raise ValueError("cells queries must be scoped by a WHERE clause")

    referenced_columns = {
        column.name for column in statement.find_all(exp.Column) if column.name
    }
    if not referenced_columns:
        raise ValueError("query must reference cells columns")
    if not referenced_columns.issubset(_ALLOWED_SQL_COLUMNS):
        raise ValueError("query references non-cells columns")
    if not referenced_columns.intersection({"row_label", "col_label"}):
        raise ValueError("query must be scoped by row_label or col_label")
