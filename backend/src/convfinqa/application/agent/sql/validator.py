from typing import Any

import sqlglot
import sqlglot.expressions as exp


def validate_select(sql: str) -> None:
    """Raises ValueError if sql is not a single bare SELECT statement."""
    try:
        statements: list[Any] = sqlglot.parse(sql, dialect="sqlite")  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"SQL parse error: {exc}") from exc

    if not statements or statements[0] is None:
        raise ValueError("empty SQL statement")

    if len(statements) > 1:
        raise ValueError("only a single SELECT statement is allowed")

    statement: Any = statements[0]

    if not isinstance(statement, exp.Select):
        raise ValueError(f"only SELECT statements are allowed, got: {type(statement).__name__}")

    _reject_dml_in_ast(statement)


_FORBIDDEN_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Transaction,
    exp.Command,
    exp.Pragma,
    exp.Attach,
)


def _reject_dml_in_ast(node: exp.Select) -> None:
    for child in node.walk():  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if isinstance(child, _FORBIDDEN_NODE_TYPES):
            raise ValueError(f"forbidden statement type in query: {type(child).__name__}")
