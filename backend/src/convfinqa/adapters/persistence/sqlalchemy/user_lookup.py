import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.models import UserOrm


class SqlAlchemyUserLookup:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(self, sub: str) -> uuid.UUID | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserOrm.id).where(UserOrm.cognito_sub == sub)
            )
            value = result.scalar_one_or_none()
            return uuid.UUID(str(value)) if value is not None else None
