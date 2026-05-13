from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from convfinqa.adapters.persistence.documents_seeder import (
    derive_title,
    iter_document_records,
    parse_document_id,
    seed,
)


@pytest.mark.unit
def test_parse_document_id_single_with_chunk_suffix() -> None:
    assert parse_document_id("Single_AAPL/2002/page_23.pdf-1") == ("AAPL", 2002, 23)


@pytest.mark.unit
def test_parse_document_id_double_without_chunk_suffix() -> None:
    assert parse_document_id("Double_UPS/2009/page_33.pdf") == ("UPS", 2009, 33)


@pytest.mark.unit
def test_parse_document_id_returns_nones_when_unrecognised() -> None:
    assert parse_document_id("garbage/no/match") == (None, None, None)


@pytest.mark.unit
def test_derive_title_includes_ticker_year_and_page() -> None:
    title = derive_title("AAPL", 2002, 23)

    assert title is not None
    assert "AAPL" in title and "2002" in title and "23" in title


@pytest.mark.unit
def test_derive_title_returns_none_when_any_field_missing() -> None:
    assert derive_title(None, 2009, 1) is None
    assert derive_title("AAPL", None, 1) is None
    assert derive_title("AAPL", 2002, None) is None


@pytest.mark.unit
def test_iter_document_records_streams_train_and_dev_with_doc_payloads(
    tmp_path: Path,
) -> None:
    dataset: dict[str, list[dict[str, Any]]] = {
        "train": [
            {
                "id": "Single_AAPL/2002/page_23.pdf-1",
                "doc": {
                    "pre_text": "pre",
                    "post_text": "post",
                    "table": {"revenue": 1.0},
                },
            }
        ],
        "dev": [
            {
                "id": "Double_UPS/2009/page_33.pdf",
                "doc": {"pre_text": "", "post_text": "", "table": {}},
            }
        ],
    }
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset))

    records = list(iter_document_records(dataset_path))

    assert {r.id for r in records} == {
        "Single_AAPL/2002/page_23.pdf-1",
        "Double_UPS/2009/page_33.pdf",
    }
    aapl = next(r for r in records if r.ticker == "AAPL")
    assert aapl.year == 2002 and aapl.page == 23
    assert aapl.table_data == {"revenue": 1.0}
    assert aapl.column_order == ["revenue"]
    assert aapl.pre_text == "pre"


@pytest.mark.unit
def test_iter_document_records_preserves_wire_column_order_for_integer_like_keys(
    tmp_path: Path,
) -> None:
    dataset: dict[str, list[dict[str, Any]]] = {
        "train": [
            {
                "id": "Single_JKHY/2009/page_28.pdf-3",
                "doc": {
                    "pre_text": "",
                    "post_text": "",
                    "table": {
                        "Year ended June 30, 2009": {"net income": 103102},
                        "2008": {"net income": 104222},
                        "2007": {"net income": 104681},
                    },
                },
            }
        ],
        "dev": [],
    }
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset))

    records = list(iter_document_records(dataset_path))

    assert records[0].column_order == [
        "Year ended June 30, 2009",
        "2008",
        "2007",
    ]


def _build_dataset(tmp_path: Path, table_data: dict[str, float]) -> Path:
    dataset: dict[str, list[dict[str, Any]]] = {
        "train": [
            {
                "id": "Single_SEEDA/2020/page_5.pdf-1",
                "doc": {
                    "pre_text": "alpha pre-text",
                    "post_text": "alpha post-text",
                    "table": table_data,
                },
            },
            {
                "id": "Double_SEEDB/2021/page_10.pdf",
                "doc": {
                    "pre_text": "beta pre-text",
                    "post_text": "beta post-text",
                    "table": {"net": 2.0},
                },
            },
        ],
        "dev": [
            {
                "id": "Single_SEEDC/2022/page_15.pdf-3",
                "doc": {
                    "pre_text": "gamma pre-text",
                    "post_text": "gamma post-text",
                    "table": {"ebitda": 3.0},
                },
            }
        ],
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset))
    return path


async def _wipe_documents(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM messages"))
        await conn.execute(text("DELETE FROM conversations"))
        await conn.execute(text("DELETE FROM documents"))


async def _count_documents(engine: AsyncEngine) -> int:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM documents"))
        return int(result.scalar_one())


async def test_seed_inserts_all_records_and_is_idempotent(
    engine: AsyncEngine, database_url: str, tmp_path: Path
) -> None:
    await _wipe_documents(engine)
    dataset_path = _build_dataset(tmp_path, table_data={"revenue": 1.0})

    first_count = await seed(database_url, dataset_path, batch_size=2)
    rows_after_first = await _count_documents(engine)

    second_count = await seed(database_url, dataset_path, batch_size=2)
    rows_after_second = await _count_documents(engine)

    assert first_count == 3
    assert rows_after_first == 3
    assert second_count == 3
    assert rows_after_second == 3


async def test_seed_upserts_overwrite_changed_fields(
    engine: AsyncEngine, database_url: str, tmp_path: Path
) -> None:
    await _wipe_documents(engine)
    initial_path = _build_dataset(tmp_path, table_data={"revenue": 1.0})
    await seed(database_url, initial_path, batch_size=10)

    updated_path = _build_dataset(tmp_path, table_data={"revenue": 999.0})
    await seed(database_url, updated_path, batch_size=10)

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT table_data FROM documents WHERE id = "
                    "'Single_SEEDA/2020/page_5.pdf-1'"
                )
            )
        ).first()

    assert row is not None
    assert row[0] == {"revenue": 999.0}


async def test_seed_persists_column_order_for_integer_like_keys(
    engine: AsyncEngine, database_url: str, tmp_path: Path
) -> None:
    await _wipe_documents(engine)
    dataset: dict[str, list[dict[str, Any]]] = {
        "train": [
            {
                "id": "Single_JKHY/2009/page_28.pdf-3",
                "doc": {
                    "pre_text": "",
                    "post_text": "",
                    "table": {
                        "Year ended June 30, 2009": {"net income": 103102},
                        "2008": {"net income": 104222},
                        "2007": {"net income": 104681},
                    },
                },
            }
        ],
        "dev": [],
    }
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(dataset))

    await seed(database_url, dataset_path, batch_size=10)

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT column_order FROM documents "
                    "WHERE id = 'Single_JKHY/2009/page_28.pdf-3'"
                )
            )
        ).first()

    assert row is not None
    assert row[0] == ["Year ended June 30, 2009", "2008", "2007"]
