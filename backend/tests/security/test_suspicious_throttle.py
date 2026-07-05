from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from convfinqa.application.suspicious_attempt_throttle import SuspiciousAttemptThrottle
from convfinqa.domain.ports.rate_limit import RateLimitPort
from tests.security.fakes import USER_ID, FakeRateLimit


def _throttle(
    rate_limit: FakeRateLimit, max_attempts: int = 3, window_seconds: int = 300
) -> SuspiciousAttemptThrottle:
    return SuspiciousAttemptThrottle(
        rate_limit=cast(RateLimitPort, rate_limit),
        max_attempts=max_attempts,
        window_seconds=window_seconds,
    )


@pytest.mark.asyncio
async def test_attempts_within_limit_are_not_throttled() -> None:
    rate_limit = FakeRateLimit()
    throttle = _throttle(rate_limit, max_attempts=3)

    decisions = [await throttle.register_blocked_attempt(USER_ID) for _ in range(3)]

    assert [d.throttled for d in decisions] == [False, False, False]
    assert [d.attempts for d in decisions] == [1, 2, 3]


@pytest.mark.asyncio
async def test_attempts_beyond_limit_are_throttled() -> None:
    rate_limit = FakeRateLimit(next_count=4)
    throttle = _throttle(rate_limit, max_attempts=3)

    decision = await throttle.register_blocked_attempt(USER_ID)

    assert decision.throttled
    assert decision.attempts == 4


@pytest.mark.asyncio
async def test_attempts_in_same_window_share_window_start() -> None:
    rate_limit = FakeRateLimit()
    throttle = _throttle(rate_limit, window_seconds=300)
    base = datetime(2026, 7, 5, 12, 1, 0, tzinfo=UTC)

    await throttle.register_blocked_attempt(USER_ID, now=base)
    await throttle.register_blocked_attempt(USER_ID, now=base + timedelta(seconds=90))

    (_, first_window, first_expiry), (_, second_window, _) = rate_limit.calls
    assert first_window == second_window
    assert first_window == datetime(2026, 7, 5, 12, 0, 0, tzinfo=UTC)
    assert first_expiry == first_window + timedelta(seconds=600)


@pytest.mark.asyncio
async def test_attempts_in_later_window_start_a_fresh_count() -> None:
    rate_limit = FakeRateLimit()
    throttle = _throttle(rate_limit, window_seconds=300)
    base = datetime(2026, 7, 5, 12, 1, 0, tzinfo=UTC)

    await throttle.register_blocked_attempt(USER_ID, now=base)
    await throttle.register_blocked_attempt(USER_ID, now=base + timedelta(seconds=600))

    (_, first_window, _), (_, second_window, _) = rate_limit.calls
    assert second_window == first_window + timedelta(seconds=600)
