import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.usefixtures("schema")
def test_pg_cron_migration_is_noop_on_stock_postgres(database_url: str) -> None:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)

    try:
        command.downgrade(config, "0007_cache_ratelimit_idempotency")
        command.upgrade(config, "head")
        pg_cron_installed = asyncio.run(_pg_cron_extension_exists(database_url))
        assert not pg_cron_installed, "pg_cron must not be installed on stock Postgres"
    finally:
        command.upgrade(config, "head")


async def _pg_cron_extension_exists(url: str) -> bool:
    engine = create_async_engine(url, poolclass=NullPool, future=True)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT count(*) FROM pg_extension WHERE extname = 'pg_cron'")
            )
            return bool(result.scalar_one())
    finally:
        await engine.dispose()
