import uuid
from datetime import datetime
from typing import Protocol


class RateLimitPort(Protocol):
    async def increment(
        self, user_id: uuid.UUID, window_start: datetime, expires_at: datetime
    ) -> int: ...
