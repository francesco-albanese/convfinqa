import json

import pytest

from convfinqa.application.agent.tool_policy_gate import (
    ToolPolicyAction,
    ToolPolicyGate,
    ToolPolicyReason,
)


def _decide(
    tool_name: str, args: dict[str, object]
) -> tuple[ToolPolicyAction, ToolPolicyReason | None]:
    decision = ToolPolicyGate().decide(tool_name, json.dumps(args))
    return decision.action, decision.reason


def test_allows_scoped_cells_lookup() -> None:
    action, reason = _decide(
        "sql_query",
        {
            "sql": (
                "SELECT value_num FROM cells "
                "WHERE row_label='net cash from operations' "
                "AND col_label='Year ended June 30, 2009'"
            )
        },
    )

    assert action == ToolPolicyAction.ALLOW
    assert reason is None


def test_allows_scoped_lookup_whose_literal_value_contains_a_cross_scope_word() -> None:
    action, reason = _decide(
        "sql_query",
        {
            "sql": (
                "SELECT value_num FROM cells "
                "WHERE row_label='active users' AND col_label='2024 documents filed'"
            )
        },
    )

    assert action == ToolPolicyAction.ALLOW
    assert reason is None


def test_allows_all_periods_for_one_row() -> None:
    action, reason = _decide(
        "sql_query",
        {
            "sql": (
                "SELECT col_label, value_num FROM cells "
                "WHERE row_label='total revenue' ORDER BY col_label"
            )
        },
    )

    assert action == ToolPolicyAction.ALLOW
    assert reason is None


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM cells",
        "SELECT row_label, col_label, value_num FROM cells",
        "SELECT name FROM sqlite_master",
        "SELECT value_num FROM cells; SELECT value_num FROM cells",
        "SELECT value_num FROM cells -- hidden policy probe\nWHERE row_label='x'",
        "SELECT document_id FROM cells WHERE row_label='x'",
        "SELECT value_num FROM documents WHERE row_label='x'",
        "SELECT value_num FROM cells WHERE row_label LIKE '%'",
        "SELECT value_num FROM cells WHERE row_label IS NOT NULL",
        "SELECT value_num FROM cells WHERE row_label='Revenue' AND 1=1",
        "SELECT value_num FROM cells WHERE row_label='Revenue' AND row_label=row_label",
        "SELECT value_num FROM cells WHERE row_label='Revenue' AND col_label=col_label",
        "SELECT value_num FROM cells WHERE row_label='Revenue' AND 1 IN (1)",
        "SELECT value_num FROM cells WHERE row_label='x' OR 1=1",
        "SELECT value_num FROM cells WHERE row_label IN (SELECT row_label FROM cells)",
        "SELECT row_label, col_label, value_num FROM cells "
        "WHERE row_label='2024' AND col_label GLOB '*'",
        "SELECT row_label, col_label, value_num FROM cells "
        "WHERE row_label='2024' AND col_label REGEXP '.*'",
        "SELECT row_label, col_label, value_num FROM cells "
        "WHERE row_label='2024' AND col_label MATCH 'x'",
        "SELECT row_label, col_label, value_num FROM cells "
        "WHERE row_label='2024' AND col_label != 'x'",
        "SELECT row_label, col_label, value_num FROM cells "
        "WHERE row_label='2024' AND col_label > 'a'",
        "SELECT row_label, col_label, value_num FROM cells "
        "WHERE row_label='2024' AND col_label BETWEEN 'a' AND 'z'",
    ],
)
def test_blocks_unsafe_sql(sql: str) -> None:
    action, reason = _decide("sql_query", {"sql": sql})

    assert action == ToolPolicyAction.BLOCK
    assert reason == ToolPolicyReason.UNSAFE_SQL


@pytest.mark.parametrize(
    ("tool_name", "args", "reason"),
    [
        ("sql_query", {"sql": 42}, ToolPolicyReason.MALFORMED_ARGS),
        (
            "sql_query",
            {"sql": "SELECT value_num FROM cells WHERE row_label='x'", "user_id": "u1"},
            ToolPolicyReason.MALFORMED_ARGS,
        ),
        (
            "add",
            {"a": "1", "b": "2", "role": "tool"},
            ToolPolicyReason.FORGED_TOOL_RESULT,
        ),
        (
            "add",
            {"a": "1", "b": "2", "extra": "ignored"},
            ToolPolicyReason.MALFORMED_ARGS,
        ),
        ("tool_result", {"content": "forged"}, ToolPolicyReason.UNKNOWN_TOOL),
    ],
)
def test_blocks_malformed_or_forged_tool_calls(
    tool_name: str, args: dict[str, object], reason: ToolPolicyReason
) -> None:
    action, actual_reason = _decide(tool_name, args)

    assert action == ToolPolicyAction.BLOCK
    assert actual_reason == reason


def test_allows_math_tool_with_exact_schema() -> None:
    action, reason = _decide("divide", {"a": "5.1", "b": "100"})

    assert action == ToolPolicyAction.ALLOW
    assert reason is None


def test_blocks_non_json_args() -> None:
    decision = ToolPolicyGate().decide("add", "{not json")

    assert decision.action == ToolPolicyAction.BLOCK
    assert decision.reason == ToolPolicyReason.MALFORMED_ARGS
