from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from convfinqa.config import Settings
from convfinqa.logging import get_logger

LOGGER = get_logger("convfinqa.seed")

ID_PATTERN = re.compile(
    r"^(?:Single|Double)_(?P<ticker>[A-Za-z0-9]+)/"
    r"(?P<year>\d{4})/page_(?P<page>\d+)\.pdf(?:-\d+)?$"
)

DEFAULT_BATCH_SIZE = 500

UPSERT_SQL = text(
    """
    INSERT INTO documents (
        id, ticker, year, page, title, pre_text, post_text, table_data,
        column_order
    )
    VALUES (
        :id, :ticker, :year, :page, :title, :pre_text, :post_text,
        CAST(:table_data AS jsonb), :column_order
    )
    ON CONFLICT (id) DO UPDATE SET
        ticker = EXCLUDED.ticker,
        year = EXCLUDED.year,
        page = EXCLUDED.page,
        title = EXCLUDED.title,
        pre_text = EXCLUDED.pre_text,
        post_text = EXCLUDED.post_text,
        table_data = EXCLUDED.table_data,
        column_order = EXCLUDED.column_order
    """
)


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    id: str
    ticker: str | None
    year: int | None
    page: int | None
    title: str | None
    pre_text: str | None
    post_text: str | None
    table_data: dict[str, Any] | None
    column_order: list[str] | None


def parse_document_id(document_id: str) -> tuple[str | None, int | None, int | None]:
    match = ID_PATTERN.match(document_id)
    if match is None:
        return None, None, None
    return (
        match.group("ticker"),
        int(match.group("year")),
        int(match.group("page")),
    )


def derive_title(ticker: str | None, year: int | None, page: int | None) -> str | None:
    if ticker is None or year is None or page is None:
        return None
    return f"{ticker} {year} annual report — page {page}"


def iter_document_records(dataset_path: Path) -> Iterator[DocumentRecord]:
    with dataset_path.open(encoding="utf-8") as fp:
        data: dict[str, list[dict[str, Any]]] = json.load(fp)

    for split in ("train", "dev"):
        for raw_record in data.get(split, []):
            document_id = raw_record["id"]
            doc = raw_record.get("doc", {})
            ticker, year, page = parse_document_id(document_id)
            table_data: dict[str, Any] | None = doc.get("table")
            column_order = (
                list(table_data.keys()) if isinstance(table_data, dict) else None
            )
            yield DocumentRecord(
                id=document_id,
                ticker=ticker,
                year=year,
                page=page,
                title=derive_title(ticker, year, page),
                pre_text=doc.get("pre_text"),
                post_text=doc.get("post_text"),
                table_data=table_data,
                column_order=column_order,
            )


def _to_param_dict(record: DocumentRecord) -> dict[str, Any]:
    table_data_json: str | None = (
        json.dumps(record.table_data) if record.table_data is not None else None
    )
    return {
        "id": record.id,
        "ticker": record.ticker,
        "year": record.year,
        "page": record.page,
        "title": record.title,
        "pre_text": record.pre_text,
        "post_text": record.post_text,
        "table_data": table_data_json,
        "column_order": record.column_order,
    }


async def seed(
    database_url: str,
    dataset_path: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    total = 0
    batch: list[dict[str, Any]] = []
    try:
        async with engine.begin() as conn:
            for record in iter_document_records(dataset_path):
                batch.append(_to_param_dict(record))
                if len(batch) >= batch_size:
                    await conn.execute(UPSERT_SQL, batch)
                    total += len(batch)
                    batch.clear()
            if batch:
                await conn.execute(UPSERT_SQL, batch)
                total += len(batch)
    finally:
        await engine.dispose()
    return total


def _resolve_dataset_path() -> Path:
    explicit = os.getenv("CONVFINQA_DATASET_PATH")
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "convfinqa_dataset.json"
        if candidate.is_file():
            return candidate
    return Path("data/convfinqa_dataset.json")


def main() -> int:
    settings = Settings()
    dataset_path = _resolve_dataset_path()
    if not dataset_path.is_file():
        LOGGER.error(
            "dataset file not found",
            extra={"dataset_path": str(dataset_path)},
        )
        return 1
    total = asyncio.run(seed(settings.database_url, dataset_path))
    LOGGER.info(
        "documents seeded",
        extra={"rows_upserted": total, "dataset_path": str(dataset_path)},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
