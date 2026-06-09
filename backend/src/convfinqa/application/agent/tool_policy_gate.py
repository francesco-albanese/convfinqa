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
    _validate_literal_scope(statement)


def _validate_literal_scope(statement: exp.Select) -> None:
    for child in statement.walk():  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if isinstance(child, exp.Or | exp.Subquery | exp.Like | exp.Is):
            raise ValueError("query scope must use literal equality or finite IN")
        if isinstance(child, exp.Select) and child is not statement:
            raise ValueError("subqueries are not allowed")
        if isinstance(child, exp.EQ | exp.In) and _is_self_contained_truth_expression(
            child
        ):
            raise ValueError("self-contained truth predicates are not allowed")

    if not any(_is_scoped_equality(node) for node in statement.find_all(exp.EQ)):
        if not any(_is_scoped_in(node) for node in statement.find_all(exp.In)):
            raise ValueError("query must be scoped by literal row_label or col_label")


def _is_scoped_equality(node: exp.EQ) -> bool:
    left = node.args.get("this")
    right = node.args.get("expression")
    return (_is_scope_column(left) and isinstance(right, exp.Literal)) or (
        _is_scope_column(right) and isinstance(left, exp.Literal)
    )


def _is_self_contained_truth_expression(node: exp.EQ | exp.In) -> bool:
    if isinstance(node, exp.EQ):
        left = node.args.get("this")
        right = node.args.get("expression")
        if isinstance(left, exp.Literal) and isinstance(right, exp.Literal):
            return True
        return (
            isinstance(left, exp.Column)
            and isinstance(right, exp.Column)
            and left.name == right.name
        )

    subject = node.args.get("this")
    expressions = node.args.get("expressions")
    return isinstance(subject, exp.Literal) and isinstance(expressions, list)


def _is_scoped_in(node: exp.In) -> bool:
    subject = node.args.get("this")
    expressions = node.args.get("expressions")
    if not isinstance(expressions, list):
        return False
    typed_expressions = cast("list[object]", expressions)
    return (
        _is_scope_column(subject)
        and bool(typed_expressions)
        and all(isinstance(item, exp.Literal) for item in typed_expressions)
    )


def _is_scope_column(node: object) -> bool:
    return isinstance(node, exp.Column) and node.name in {"row_label", "col_label"}
