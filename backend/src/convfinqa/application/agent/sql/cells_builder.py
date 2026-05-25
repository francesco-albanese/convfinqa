import sqlite3
from typing import Any, cast

from convfinqa.domain.entities import Document

CELLS_SCHEMA = """
CREATE TABLE cells (
    row_label TEXT,
    col_label TEXT,
    ordinal   INTEGER,
    value_num REAL,
    value_text TEXT
)
"""


def build_cells_db(document: Document) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(CELLS_SCHEMA)

    table_data: dict[str, Any] = document.table_data or {}
    column_order = list(document.column_order) if document.column_order else list(table_data.keys())

    for col_label in column_order:
        if col_label not in table_data:
            continue
        row_dict: Any = table_data[col_label]
        if not isinstance(row_dict, dict):
            continue
        typed_row: dict[str, Any] = cast("dict[str, Any]", row_dict)
        ordinal_counter: dict[str, int] = {}
        for row_label, cell_value in typed_row.items():
            ordinal = ordinal_counter.get(row_label, 0)
            ordinal_counter[row_label] = ordinal + 1
            value_num: float | None = None
            value_text: str | None = None
            try:
                value_num = float(cell_value)
            except (TypeError, ValueError):
                value_text = str(cell_value) if cell_value is not None else None
            conn.execute(
                "INSERT INTO cells (row_label, col_label, ordinal, value_num, value_text) VALUES (?, ?, ?, ?, ?)",
                (row_label, col_label, ordinal, value_num, value_text),
            )

    conn.commit()
    return conn
