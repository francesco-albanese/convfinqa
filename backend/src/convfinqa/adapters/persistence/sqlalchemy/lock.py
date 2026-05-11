from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

ADVISORY_LOCK_SQL = text("SELECT pg_try_advisory_xact_lock(hashtextextended(:cid, 0))")


class SqlAlchemyConversationLock:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def try_acquire(self, conversation_id: str) -> AbstractAsyncContextManager[bool]:
        return self._scope(conversation_id)

    @asynccontextmanager
    async def _scope(self, conversation_id: str) -> AsyncGenerator[bool]:
        async with self._session_factory() as session, session.begin():
            result = await session.execute(ADVISORY_LOCK_SQL, {"cid": conversation_id})
            yield bool(result.scalar_one())
