from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.models import OutputCacheOrm


class PostgresCacheAdapter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, prompt_hash: str, model: str) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(OutputCacheOrm.response).where(
                    OutputCacheOrm.prompt_hash == prompt_hash,
                    OutputCacheOrm.model == model,
                    OutputCacheOrm.expires_at > func.now(),
                )
            )
            return result.scalar_one_or_none()

    async def set(
        self, prompt_hash: str, model: str, response: dict[str, Any], ttl_seconds: int
    ) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        stmt = (
            insert(OutputCacheOrm)
            .values(
                prompt_hash=prompt_hash,
                model=model,
                response=response,
                expires_at=expires_at,
            )
            .on_conflict_do_update(
                constraint="pk_output_cache",
                set_={
                    "response": response,
                    "expires_at": expires_at,
                    "created_at": func.now(),
                },
            )
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(stmt)

    async def delete(self, prompt_hash: str, model: str) -> None:
        async with self._session_factory() as session, session.begin():
            row = await session.get(OutputCacheOrm, (prompt_hash, model))
            if row is not None:
                await session.delete(row)
