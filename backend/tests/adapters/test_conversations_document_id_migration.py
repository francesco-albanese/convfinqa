import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

PROJECT_ROOT = Path(__file__).resolve().parents[3]


async def test_conversations_document_id_foreign_key_rejects_unknown_document(
    engine: AsyncEngine,
) -> None:
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO conversations (id, user_id, document_id) "
                    "VALUES ('conv_a', 'alice', 'this-doc-does-not-exist')"
                )
            )


async def test_conversations_document_id_is_not_null(
    engine: AsyncEngine,
) -> None:
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO conversations (id, user_id) VALUES ('conv_b', 'alice')"
                )
            )


@pytest.mark.usefixtures("schema")
def test_migration_downgrade_drops_document_id_then_upgrade_restores(
    database_url: str,
) -> None:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    try:
        command.downgrade(config, "0002_documents_table")
        assert asyncio.run(_column_exists(database_url, "document_id")) is False
    finally:
        command.upgrade(config, "head")
    assert asyncio.run(_column_exists(database_url, "document_id")) is True


async def _column_exists(url: str, column: str) -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(url, poolclass=NullPool, future=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'conversations' AND column_name = :col"
                ),
                {"col": column},
            )
            return result.scalar() is not None
    finally:
        await engine.dispose()
