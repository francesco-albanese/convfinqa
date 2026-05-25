import asyncio
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parents[3]


async def test_insert_and_select_user(engine: AsyncEngine) -> None:
    sub = f"google-oauth2|{uuid.uuid4().hex}"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (cognito_sub, email) VALUES (:cognito_sub, :email)"
            ),
            {"cognito_sub": sub, "email": "alice@example.com"},
        )

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT id, cognito_sub, email FROM users WHERE cognito_sub = :sub"
                ),
                {"sub": sub},
            )
        ).one()

    assert str(row[1]) == sub
    assert row[2] == "alice@example.com"
    assert uuid.UUID(str(row[0]))


async def test_cognito_sub_unique_constraint_rejects_duplicate(
    engine: AsyncEngine,
) -> None:
    sub = f"google-oauth2|{uuid.uuid4().hex}"
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO users (cognito_sub, email) VALUES (:sub, :email)"),
            {"sub": sub, "email": "first@example.com"},
        )

    with pytest.raises(Exception, match="unique"):
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO users (cognito_sub, email) VALUES (:sub, :email)"),
                {"sub": sub, "email": "second@example.com"},
            )


@pytest.mark.usefixtures("schema")
def test_migration_downgrade_drops_users_then_upgrade_recreates(
    database_url: str,
) -> None:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    try:
        command.downgrade(config, "0004_documents_column_order")
        assert asyncio.run(_users_table_exists(database_url)) is False
    finally:
        command.upgrade(config, "head")


async def _users_table_exists(url: str) -> bool:
    engine = create_async_engine(url, poolclass=NullPool, future=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT to_regclass('public.users') IS NOT NULL")
            )
            return bool(result.scalar())
    finally:
        await engine.dispose()
