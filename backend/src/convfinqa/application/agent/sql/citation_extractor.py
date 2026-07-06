from typing import Any

import sqlglot
import sqlglot.expressions as exp


def extract_citations(sql: str) -> list[tuple[str, str]]:
    """
    Returns list of (row_label, col_label) from WHERE equality and IN predicates.
    Only returns a pair when BOTH row_label and col_label are bound to string literals.
    Returns [] on any parse error or if predicates are absent.
    """
    try:
        statements: list[Any] = sqlglot.parse(sql, dialect="sqlite")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    except Exception:  # noqa: BLE001
        return []

    if not statements or statements[0] is None:
        return []

    statement: Any = statements[0]
    if not isinstance(statement, exp.Select):
        return []

    where: Any = statement.args.get("where")  # pyright: ignore[reportUnknownMemberType]
    if where is None:
        return []

    row_labels: list[str] = []
    col_labels: list[str] = []

    _collect_values(where, "row_label", row_labels)
    _collect_values(where, "col_label", col_labels)

    if not row_labels or not col_labels:
        return []

    return [(r, c) for r in row_labels for c in col_labels]


def _collect_values(node: Any, column_name: str, out: list[str]) -> None:
    for expr in node.walk():  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if isinstance(expr, exp.EQ):
            _try_eq_literal(expr, column_name, out)
        elif isinstance(expr, exp.In):
            _try_in_literals(expr, column_name, out)


def _try_eq_literal(eq: exp.EQ, column_name: str, out: list[str]) -> None:
    left: Any = eq.left  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    right: Any = eq.right  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    if (
        _is_column(left, column_name)
        and isinstance(right, exp.Literal)
        and right.is_string
    ):
        out.append(right.this)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
    elif (
        _is_column(right, column_name)
        and isinstance(left, exp.Literal)
        and left.is_string
    ):
        out.append(left.this)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]


def _try_in_literals(in_expr: exp.In, column_name: str, out: list[str]) -> None:
    this: Any = in_expr.this  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    if not _is_column(this, column_name):
        return
    for item in in_expr.expressions:  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if isinstance(item, exp.Literal) and item.is_string:
            out.append(item.this)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]


def _is_column(node: Any, name: str) -> bool:
    return isinstance(node, exp.Column) and node.name.lower() == name.lower()  # pyright: ignore[reportUnknownMemberType]
