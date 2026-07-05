import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from convfinqa.domain.ports.rate_limit import RateLimitPort

SUSPICIOUS_ACTIVITY_REFUSAL = (
    "Too many requests were blocked by safety policies in a short period. "
    "Please wait a few minutes before trying again."
)


@dataclass(frozen=True, slots=True)
class ThrottleDecision:
    throttled: bool
    attempts: int


class SuspiciousAttemptThrottle:
    def __init__(
        self,
        rate_limit: RateLimitPort,
        max_attempts: int,
        window_seconds: int,
    ) -> None:
        self._rate_limit = rate_limit
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    async def register_blocked_attempt(
        self, user_id: uuid.UUID, now: datetime | None = None
    ) -> ThrottleDecision:
        moment = now or datetime.now(UTC)
        if moment.tzinfo is None:
            raise ValueError("now must be timezone-aware to keep windows UTC-aligned")
        window_start = self._window_start(moment)
        expires_at = window_start + timedelta(seconds=self._window_seconds * 2)
        attempts = await self._rate_limit.increment(user_id, window_start, expires_at)
        return ThrottleDecision(
            throttled=attempts > self._max_attempts, attempts=attempts
        )

    def _window_start(self, moment: datetime) -> datetime:
        epoch_seconds = int(moment.timestamp())
        floored = epoch_seconds - (epoch_seconds % self._window_seconds)
        return datetime.fromtimestamp(floored, tz=UTC)
