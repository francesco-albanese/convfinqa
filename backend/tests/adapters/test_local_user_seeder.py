import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from convfinqa.adapters.persistence.local_user_seeder import seed

pytestmark = pytest.mark.integration


async def test_seed_is_idempotent_and_updates_email(
    database_url: str,
    engine: AsyncEngine,
    schema: None,
) -> None:
    user_id = uuid.UUID("00000000-0000-4000-8000-000000000099")
    try:
        await seed(database_url, user_id, "first@convfinqa.test")
        await seed(database_url, user_id, "local@convfinqa.test")

        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT cognito_sub, email FROM users WHERE id = :id"),
                {"id": user_id},
            )
            assert result.one() == (
                f"local:{user_id}",
                "local@convfinqa.test",
            )
    finally:
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM users WHERE id = :id"), {"id": user_id}
            )
