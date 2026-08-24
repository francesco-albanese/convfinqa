import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration


async def test_me_identifies_local_auth_mode_and_email(
    app: FastAPI,
    seeded_user_id: str,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/me",
            headers={
                "X-User-Id": seeded_user_id,
                "X-User-Email": "local@convfinqa.test",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Auth-Mode"] == "local"
    assert response.json() == {
        "user_id": seeded_user_id,
        "email": "local@convfinqa.test",
    }
