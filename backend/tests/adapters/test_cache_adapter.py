import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.cache.postgres import PostgresCacheAdapter

MODEL = "bedrock/anthropic.claude-3-5-sonnet"


def _hash() -> str:
    return f"hash-{uuid.uuid4().hex}"


@pytest.fixture
def cache(session_factory: async_sessionmaker[AsyncSession]) -> PostgresCacheAdapter:
    return PostgresCacheAdapter(session_factory)


async def test_miss_returns_none(cache: PostgresCacheAdapter) -> None:
    result = await cache.get(_hash(), MODEL)
    assert result is None


async def test_set_then_get_returns_response(cache: PostgresCacheAdapter) -> None:
    prompt_hash = _hash()
    response = {"choices": [{"message": {"content": "hello"}}]}

    await cache.set(prompt_hash, MODEL, response, ttl_seconds=3600)
    result = await cache.get(prompt_hash, MODEL)

    assert result == response


async def test_expired_entry_is_skipped(
    cache: PostgresCacheAdapter, engine: AsyncEngine
) -> None:
    prompt_hash = _hash()
    past = datetime.now(UTC) - timedelta(hours=1)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO output_cache (prompt_hash, model, response, expires_at) "
                "VALUES (:ph, :model, CAST(:resp AS jsonb), :expires_at)"
            ),
            {
                "ph": prompt_hash,
                "model": MODEL,
                "resp": '{"stale": true}',
                "expires_at": past,
            },
        )

    result = await cache.get(prompt_hash, MODEL)
    assert result is None


async def test_overwrite_on_set_updates_response(cache: PostgresCacheAdapter) -> None:
    prompt_hash = _hash()
    original = {"answer": "v1"}
    updated = {"answer": "v2"}

    await cache.set(prompt_hash, MODEL, original, ttl_seconds=3600)
    await cache.set(prompt_hash, MODEL, updated, ttl_seconds=7200)

    result = await cache.get(prompt_hash, MODEL)
    assert result == updated


async def test_delete_removes_entry(cache: PostgresCacheAdapter) -> None:
    prompt_hash = _hash()
    await cache.set(prompt_hash, MODEL, {"data": 1}, ttl_seconds=3600)

    await cache.delete(prompt_hash, MODEL)

    assert await cache.get(prompt_hash, MODEL) is None
