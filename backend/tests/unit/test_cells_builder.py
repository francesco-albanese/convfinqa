from convfinqa.application.agent.sql.cells_builder import build_cells_db
from convfinqa.domain.entities import Document


def _doc(**kwargs: object) -> Document:
    defaults = dict(
        id="doc1",
        ticker=None,
        year=None,
        page=None,
        title=None,
        pre_text=None,
        post_text=None,
        table_data=None,
        column_order=None,
    )
    return Document(**{**defaults, **kwargs})  # type: ignore[arg-type]


def test_numeric_cells_populate_value_num() -> None:
    doc = _doc(table_data={"2009": {"revenue": "1234.5"}})
    conn = build_cells_db(doc)
    row = conn.execute(
        "SELECT value_num, value_text FROM cells WHERE row_label='revenue' AND col_label='2009'"
    ).fetchone()
    assert row is not None
    assert row[0] == 1234.5
    assert row[1] is None


def test_nonnumeric_cells_populate_value_text() -> None:
    doc = _doc(table_data={"2009": {"note": "see footnote"}})
    conn = build_cells_db(doc)
    row = conn.execute(
        "SELECT value_num, value_text FROM cells WHERE row_label='note' AND col_label='2009'"
    ).fetchone()
    assert row is not None
    assert row[0] is None
    assert row[1] == "see footnote"


def test_ordinal_starts_at_zero_for_unique_row_labels() -> None:
    doc = _doc(table_data={"2009": {"Total": "100", "Sub-total": "60"}})
    conn = build_cells_db(doc)
    rows = conn.execute(
        "SELECT ordinal FROM cells WHERE col_label='2009' ORDER BY ordinal"
    ).fetchall()
    ordinals = [r[0] for r in rows]
    assert ordinals == [0, 0]


def test_column_order_controls_iteration() -> None:
    doc = _doc(
        table_data={"A": {"x": "1"}, "B": {"x": "2"}},
        column_order=("B", "A"),
    )
    conn = build_cells_db(doc)
    rows = conn.execute(
        "SELECT col_label FROM cells WHERE row_label='x' ORDER BY rowid"
    ).fetchall()
    col_labels = [r[0] for r in rows]
    assert col_labels == ["B", "A"]


def test_empty_document_produces_empty_cells_table() -> None:
    doc = _doc(table_data=None)
    conn = build_cells_db(doc)
    count = conn.execute("SELECT COUNT(*) FROM cells").fetchone()[0]
    assert count == 0
