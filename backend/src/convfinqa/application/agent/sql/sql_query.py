import logging
import sqlite3
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from convfinqa.application.agent.sql.cells_builder import build_cells_db
from convfinqa.application.agent.sql.validator import validate_select
from convfinqa.domain.entities import Document
from convfinqa.logging import get_logger

CELLS_ROW_LIMIT = 100
TRUNCATION_SUFFIX = "...[limit reached]"

logger = get_logger("convfinqa.sql_query")

SQL_QUERY_DOC = """\
## sql_query(sql)
Purpose: Execute a SELECT query against the pinned document's financial table cells.
ALWAYS call sql_query before any arithmetic — never guess a cell value, always look it up.

Schema: cells(row_label TEXT, col_label TEXT, ordinal INTEGER, value_num REAL NULL, value_text TEXT NULL)
  - row_label: the row identifier from the financial table
  - col_label: the column identifier (e.g. fiscal year label)
  - ordinal: disambiguates duplicate row_labels within the same col (0 = first occurrence)
  - value_num: numeric value if cell is numeric, else NULL
  - value_text: text value if cell is non-numeric, else NULL

Args: sql (SELECT statement string).
Returns: rows (list of dicts), truncated (bool, true if result capped at 100 rows).

Example queries:
  Single-cell lookup:
    SELECT value_num FROM cells WHERE row_label='net cash from operating activities' AND col_label='Year ended June 30, 2009'

  All periods for a row:
    SELECT col_label, value_num FROM cells WHERE row_label='total revenue' ORDER BY col_label

  Sum of multiple items for one period:
    SELECT SUM(value_num) FROM cells WHERE row_label IN ('item1', 'item2') AND col_label='Year ended June 30, 2009'\
"""


class SqlQueryInput(BaseModel):
    sql: str


class SqlQueryOutput(BaseModel):
    rows: list[dict[str, str | float | None]]
    truncated: bool


def sql_query(document: Document, sql: str) -> dict[str, Any]:
    """
    Validate, build cells SQLite, execute query, return rows.
    Raises ValueError on validation failure or sqlite3 error.
    """
    validate_select(sql)

    conn = build_cells_db(document)
    try:
        cursor = conn.execute(sql)
        column_names = [description[0] for description in (cursor.description or [])]
        raw_rows = cursor.fetchmany(CELLS_ROW_LIMIT + 1)
    except sqlite3.Error as exc:
        logger.log(
            logging.WARNING,
            "sql_query_execution_error",
            extra={
                "exc_type": exc.__class__.__name__,
                "exc_message": str(exc),
            },
        )
        raise ValueError("sql_query failed") from exc
    finally:
        conn.close()

    truncated = len(raw_rows) > CELLS_ROW_LIMIT
    rows_to_return = raw_rows[:CELLS_ROW_LIMIT]

    rows: list[dict[str, str | float | None]] = [
        {col: val for col, val in zip(column_names, row, strict=True)}
        for row in rows_to_return
    ]

    return SqlQueryOutput(rows=rows, truncated=truncated).model_dump()


def get_sql_query_callable(document: Document) -> Callable[..., Any]:
    def bound_sql_query(sql: str) -> dict[str, Any]:
        return sql_query(document, sql)

    return bound_sql_query
