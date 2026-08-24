from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from convfinqa.config import Settings
from convfinqa.logging import get_logger

LOGGER = get_logger("convfinqa.local_user_seed")

UPSERT_LOCAL_USER_SQL = text(
    """
    INSERT INTO users (id, cognito_sub, email)
    VALUES (CAST(:id AS uuid), :cognito_sub, :email)
    ON CONFLICT (id) DO UPDATE SET
        cognito_sub = EXCLUDED.cognito_sub,
        email = EXCLUDED.email,
        updated_at = now()
    """
)


async def seed(database_url: str, user_id: uuid.UUID, email: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                UPSERT_LOCAL_USER_SQL,
                {
                    "id": str(user_id),
                    "cognito_sub": f"local:{user_id}",
                    "email": email,
                },
            )
    finally:
        await engine.dispose()


def main() -> int:
    raw_user_id = os.getenv("LOCAL_USER_ID")
    if not raw_user_id:
        return 0
    try:
        user_id = uuid.UUID(raw_user_id)
    except ValueError:
        LOGGER.error("LOCAL_USER_ID must be a valid UUID")
        return 1

    email = os.getenv("LOCAL_USER_EMAIL", "local@convfinqa.test").strip()
    if not email:
        LOGGER.error("LOCAL_USER_EMAIL must not be empty")
        return 1

    asyncio.run(seed(Settings().database_url, user_id, email))
    LOGGER.info("local user seeded", extra={"user_id": str(user_id)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
