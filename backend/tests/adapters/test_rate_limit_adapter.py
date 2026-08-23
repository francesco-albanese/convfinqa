import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.rate_limit.postgres import PostgresRateLimitAdapter

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SCOPE = "suspicious_attempt"
_EPOCH = datetime(2099, 1, 1, tzinfo=UTC)


def _window() -> tuple[datetime, datetime]:
    offset_secs = uuid.uuid4().int % 10_000_000
    start = _EPOCH + timedelta(seconds=offset_secs)
    return start, start + timedelta(hours=1)


@pytest.fixture
def rate_limit(
    session_factory: async_sessionmaker[AsyncSession],
) -> PostgresRateLimitAdapter:
    return PostgresRateLimitAdapter(session_factory)


async def test_first_increment_creates_row_with_count_one(
    rate_limit: PostgresRateLimitAdapter,
) -> None:
    window_start, expires_at = _window()
    count = await rate_limit.increment(SCOPE, USER_ID, window_start, expires_at)
    assert count == 1


async def test_subsequent_increment_increments_existing_row(
    rate_limit: PostgresRateLimitAdapter,
) -> None:
    window_start, expires_at = _window()
    await rate_limit.increment(SCOPE, USER_ID, window_start, expires_at)
    count = await rate_limit.increment(SCOPE, USER_ID, window_start, expires_at)
    assert count == 2


async def test_scope_is_part_of_counter_identity(
    rate_limit: PostgresRateLimitAdapter,
) -> None:
    window_start, expires_at = _window()
    await rate_limit.increment(SCOPE, USER_ID, window_start, expires_at)

    count = await rate_limit.increment("api_request", USER_ID, window_start, expires_at)

    assert count == 1


async def test_concurrent_increments_are_atomic(
    rate_limit: PostgresRateLimitAdapter,
) -> None:
    window_start, expires_at = _window()

    results = await asyncio.gather(
        *[
            rate_limit.increment(SCOPE, USER_ID, window_start, expires_at)
            for _ in range(10)
        ]
    )

    assert sorted(results) == list(range(1, 11))
