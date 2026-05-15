import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.usefixtures("schema")
def test_migration_downgrade_drops_all_three_tables_then_upgrade_recreates(
    database_url: str,
) -> None:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    try:
        command.downgrade(config, "0006_conversations_user_id_fk")
        exists = asyncio.run(_tables_exist(database_url))
        assert exists == (False, False, False), "all three tables should be dropped"
    finally:
        command.upgrade(config, "head")


async def test_rate_limit_cascade_deletes_on_user_delete(
    engine: AsyncEngine,
) -> None:
    user_id = uuid.uuid4()
    window_start = datetime.now(UTC)
    expires_at = window_start + timedelta(hours=1)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, cognito_sub, email) "
                "VALUES (CAST(:id AS uuid), :sub, :email)"
            ),
            {"id": str(user_id), "sub": f"sub-{user_id.hex}", "email": "rl@example.com"},
        )
        await conn.execute(
            text(
                "INSERT INTO rate_limit (user_id, window_start, count, expires_at) "
                "VALUES (CAST(:user_id AS uuid), :window_start, 1, :expires_at)"
            ),
            {
                "user_id": str(user_id),
                "window_start": window_start,
                "expires_at": expires_at,
            },
        )

    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM users WHERE id = CAST(:id AS uuid)"),
            {"id": str(user_id)},
        )

    async with engine.connect() as conn:
        count = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM rate_limit "
                    "WHERE user_id = CAST(:id AS uuid)"
                ),
                {"id": str(user_id)},
            )
        ).scalar()

    assert count == 0, "rate_limit rows must cascade-delete with the user"


async def test_idempotency_keys_cascade_deletes_on_user_delete(
    engine: AsyncEngine,
) -> None:
    user_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(hours=24)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, cognito_sub, email) "
                "VALUES (CAST(:id AS uuid), :sub, :email)"
            ),
            {
                "id": str(user_id),
                "sub": f"sub-{user_id.hex}",
                "email": "idem@example.com",
            },
        )
        await conn.execute(
            text(
                "INSERT INTO idempotency_keys (user_id, key, response, expires_at) "
                "VALUES (CAST(:user_id AS uuid), :key, "
                "CAST(:response AS jsonb), :expires_at)"
            ),
            {
                "user_id": str(user_id),
                "key": "req-abc123",
                "response": '{"status": 200}',
                "expires_at": expires_at,
            },
        )

    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM users WHERE id = CAST(:id AS uuid)"),
            {"id": str(user_id)},
        )

    async with engine.connect() as conn:
        count = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM idempotency_keys "
                    "WHERE user_id = CAST(:id AS uuid)"
                ),
                {"id": str(user_id)},
            )
        ).scalar()

    assert count == 0, "idempotency_key rows must cascade-delete with the user"


async def _tables_exist(url: str) -> tuple[bool, bool, bool]:
    engine = create_async_engine(url, poolclass=NullPool, future=True)
    try:
        async with engine.connect() as conn:
            results = await conn.execute(
                text(
                    "SELECT "
                    "  to_regclass('public.rate_limit') IS NOT NULL, "
                    "  to_regclass('public.output_cache') IS NOT NULL, "
                    "  to_regclass('public.idempotency_keys') IS NOT NULL"
                )
            )
            row = results.one()
            return (bool(row[0]), bool(row[1]), bool(row[2]))
    finally:
        await engine.dispose()
