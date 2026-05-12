import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parents[3]


async def test_full_text_search_matches_on_title_ticker_and_pre_text(
    engine: AsyncEngine,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO documents (id, ticker, year, page, title, pre_text, "
                "post_text, table_data) "
                "VALUES (:id, :ticker, :year, :page, :title, :pre_text, "
                ":post_text, CAST(:table_data AS jsonb))"
            ),
            {
                "id": "Single_JKHY/2009/page_28.pdf-3",
                "ticker": "JKHY",
                "year": 2009,
                "page": 28,
                "title": "JKHY 2009 annual report",
                "pre_text": "credit union systems revenue grew",
                "post_text": "",
                "table_data": "{}",
            },
        )

    async with engine.connect() as conn:
        matches = (
            await conn.execute(
                text(
                    "SELECT id FROM documents "
                    "WHERE search_tsv @@ plainto_tsquery('english', :q)"
                ),
                {"q": "jkhy"},
            )
        ).all()

    assert [row[0] for row in matches] == ["Single_JKHY/2009/page_28.pdf-3"]


async def test_year_range_filter_returns_only_in_window(
    engine: AsyncEngine,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO documents (id, ticker, year, page, title, pre_text) "
                "VALUES "
                "('a', 'AAA', 2008, 1, 'A', ''), "
                "('b', 'BBB', 2012, 1, 'B', ''), "
                "('c', 'CCC', 2020, 1, 'C', '')"
            )
        )

    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT id FROM documents "
                    "WHERE year BETWEEN :lo AND :hi ORDER BY id"
                ),
                {"lo": 2010, "hi": 2015},
            )
        ).all()

    assert [row[0] for row in rows] == ["b"]


async def test_required_indexes_present(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE tablename = 'documents'"
                )
            )
        ).all()

    by_name = {row[0]: row[1] for row in rows}
    assert "USING gin" in by_name["ix_documents_search_tsv"]
    assert "USING btree (year)" in by_name["ix_documents_year"]
    assert "USING btree (ticker, year)" in by_name["ix_documents_ticker_year"]


@pytest.mark.usefixtures("schema")
def test_migration_downgrade_drops_documents_then_upgrade_recreates(
    database_url: str,
) -> None:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    try:
        command.downgrade(config, "0001_initial")
        assert asyncio.run(_documents_table_exists(database_url)) is False
    finally:
        command.upgrade(config, "head")


async def _documents_table_exists(url: str) -> bool:
    engine = create_async_engine(url, poolclass=NullPool, future=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT to_regclass('public.documents') IS NOT NULL")
            )
            return bool(result.scalar())
    finally:
        await engine.dispose()
