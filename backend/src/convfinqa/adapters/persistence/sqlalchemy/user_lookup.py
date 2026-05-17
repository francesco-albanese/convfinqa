import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.models import UserOrm
from convfinqa.domain.ports.session import UserRecord


class SqlAlchemyUserLookup:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(self, sub: str) -> UserRecord | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserOrm.id, UserOrm.email).where(UserOrm.cognito_sub == sub)
            )
            row = result.one_or_none()
            if row is None:
                return None
            user_id_raw, email_raw = row
            return UserRecord(user_id=uuid.UUID(str(user_id_raw)), email=str(email_raw))
