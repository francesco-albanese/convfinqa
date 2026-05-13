from __future__ import annotations

import base64
import binascii
import json
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.domain.entities import (
    Document,
    DocumentListPage,
    DocumentSummary,
)
from convfinqa.domain.ports.documents_port import (
    InvalidCursorError,
    ListDocumentsQuery,
)


def _encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_cursor(cursor: str) -> dict[str, Any]:
    padding = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode((cursor + padding).encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorError("malformed cursor") from exc
    if not isinstance(decoded, dict):
        raise InvalidCursorError("cursor payload is not an object")
    return cast(dict[str, Any], decoded)


class SqlAlchemyDocumentsRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, document_id: str) -> Document | None:
        sql = text(
            "SELECT id, ticker, year, page, title, pre_text, post_text, "
            "table_data, column_order "
            "FROM documents WHERE id = :id"
        )
        async with self._session_factory() as session:
            row = (await session.execute(sql, {"id": document_id})).first()
        if row is None:
            return None
        raw_column_order = row[8]
        return Document(
            id=row[0],
            ticker=row[1],
            year=row[2],
            page=row[3],
            title=row[4],
            pre_text=row[5],
            post_text=row[6],
            table_data=row[7],
            column_order=tuple(raw_column_order) if raw_column_order is not None else None,
        )

    async def list(self, query: ListDocumentsQuery) -> DocumentListPage:
        page_size = max(1, query.limit)
        params: dict[str, Any] = {
            "year_min": query.year_min,
            "year_max": query.year_max,
            "limit_plus_one": page_size + 1,
        }
        cursor_payload = _decode_cursor(query.cursor) if query.cursor else None

        if query.q:
            params["q"] = query.q
            rows, has_more = await self._run_ranked(
                params, page_size, cursor_payload
            )
            items = tuple(
                DocumentSummary(
                    id=row[0], ticker=row[1], year=row[2], page=row[3], title=row[4]
                )
                for row in rows[:page_size]
            )
            next_cursor: str | None = None
            if has_more and items:
                last_row = rows[page_size - 1]
                next_cursor = _encode_cursor({"rank": float(last_row[5]), "id": last_row[0]})
            return DocumentListPage(items=items, next_cursor=next_cursor)

        rows, has_more = await self._run_unranked(
            params, page_size, cursor_payload
        )
        items = tuple(
            DocumentSummary(
                id=row[0], ticker=row[1], year=row[2], page=row[3], title=row[4]
            )
            for row in rows[:page_size]
        )
        next_cursor = None
        if has_more and items:
            next_cursor = _encode_cursor({"id": items[-1].id})
        return DocumentListPage(items=items, next_cursor=next_cursor)

    async def _run_unranked(
        self,
        params: dict[str, Any],
        page_size: int,
        cursor_payload: dict[str, Any] | None,
    ) -> tuple[list[Any], bool]:
        cursor_id: str | None = None
        if cursor_payload is not None:
            raw = cursor_payload.get("id")
            if not isinstance(raw, str):
                raise InvalidCursorError("cursor missing 'id'")
            cursor_id = raw
        params["cursor_id"] = cursor_id
        sql = text(
            "SELECT id, ticker, year, page, title "
            "FROM documents "
            "WHERE (CAST(:year_min AS int) IS NULL OR year >= :year_min) "
            "  AND (CAST(:year_max AS int) IS NULL OR year <= :year_max) "
            "  AND (CAST(:cursor_id AS text) IS NULL OR id > :cursor_id) "
            "ORDER BY id ASC "
            "LIMIT :limit_plus_one"
        )
        async with self._session_factory() as session:
            result = await session.execute(sql, params)
            rows = list(result.all())
        return rows, len(rows) > page_size

    async def _run_ranked(
        self,
        params: dict[str, Any],
        page_size: int,
        cursor_payload: dict[str, Any] | None,
    ) -> tuple[list[Any], bool]:
        cursor_rank: float | None = None
        cursor_id: str | None = None
        if cursor_payload is not None:
            raw_rank = cursor_payload.get("rank")
            raw_id = cursor_payload.get("id")
            if not isinstance(raw_rank, int | float) or not isinstance(raw_id, str):
                raise InvalidCursorError("cursor missing 'rank' or 'id'")
            cursor_rank = float(raw_rank)
            cursor_id = raw_id
        params["cursor_rank"] = cursor_rank
        params["cursor_id"] = cursor_id
        sql = text(
            "SELECT id, ticker, year, page, title, rank "
            "FROM ( "
            "  SELECT id, ticker, year, page, title, "
            "         ts_rank(search_tsv, plainto_tsquery('english', :q)) AS rank "
            "  FROM documents "
            "  WHERE search_tsv @@ plainto_tsquery('english', :q) "
            "    AND (CAST(:year_min AS int) IS NULL OR year >= :year_min) "
            "    AND (CAST(:year_max AS int) IS NULL OR year <= :year_max) "
            ") AS ranked "
            "WHERE CAST(:cursor_rank AS float8) IS NULL "
            "   OR rank < :cursor_rank "
            "   OR (rank = :cursor_rank AND id > :cursor_id) "
            "ORDER BY rank DESC, id ASC "
            "LIMIT :limit_plus_one"
        )
        async with self._session_factory() as session:
            result = await session.execute(sql, params)
            rows = list(result.all())
        return rows, len(rows) > page_size
