import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

UPSERT_SQL = text(
    "INSERT INTO rate_limit (user_id, window_start, count, expires_at) "
    "VALUES (CAST(:user_id AS uuid), :window_start, 1, :expires_at) "
    "ON CONFLICT (user_id, window_start) "
    "DO UPDATE SET count = rate_limit.count + 1 "
    "RETURNING count"
)


class PostgresRateLimitAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def increment(
        self, user_id: uuid.UUID, window_start: datetime, expires_at: datetime
    ) -> int:
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                UPSERT_SQL,
                {
                    "user_id": str(user_id),
                    "window_start": window_start,
                    "expires_at": expires_at,
                },
            )
            return int(result.scalar_one())
