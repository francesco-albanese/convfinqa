import uuid
from dataclasses import dataclass
from typing import Annotated

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI, status
from httpx import ASGITransport, AsyncClient

from convfinqa.config import Settings
from convfinqa.container import for_testing
from convfinqa.domain.ports.session import SessionVerificationError, ValidatedClaims
from convfinqa.entrypoints.api.dependencies import get_current_user_id
from convfinqa.entrypoints.api.errors import install_exception_handlers
from convfinqa.entrypoints.api.middleware.auth import AuthMiddleware
from tests.conftest import SEEDED_USER_UUID

pytestmark = pytest.mark.unit

_USER_UUID = uuid.UUID(SEEDED_USER_UUID)
_TOKEN_VALID = "valid-token"
_TOKEN_EXPIRED = "expired-token"
_TOKEN_NO_DB_USER = "no-db-user-token"
_UNAUTHORIZED_TYPE = "https://convfinqa.local/problems/unauthorized"


@dataclass
class FakeSessionPort:
    user_id: uuid.UUID | None = _USER_UUID

    async def verify_access_token(self, token: str) -> ValidatedClaims:
        if token == _TOKEN_EXPIRED:
            raise SessionVerificationError("Token expired")
        if token == _TOKEN_NO_DB_USER:
            return ValidatedClaims(sub="unknown-sub", exp=9999999999, user_id=None)
        return ValidatedClaims(sub="test-sub", exp=9999999999, user_id=self.user_id)


def _make_app(session: FakeSessionPort | None) -> FastAPI:
    app = FastAPI(title="test")
    app.add_middleware(AuthMiddleware)
    install_exception_handlers(app)

    @app.get("/protected")
    async def protected(
        user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    ) -> dict[str, str]:
        return {"user_id": str(user_id)}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    settings = Settings()
    container = for_testing(
        settings=settings,
        engine=None,  # type: ignore[arg-type]
        session_factory=None,  # type: ignore[arg-type]
        llm=None,  # type: ignore[arg-type]
        session=session,
    )
    app.state.container = container
    return app


@pytest_asyncio.fixture(loop_scope="session")
async def authed_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=_make_app(session=FakeSessionPort())),
        base_url="http://test",
    )


@pytest_asyncio.fixture(loop_scope="session")
async def no_session_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=_make_app(session=None)),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_missing_cookie_returns_401(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/protected")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    body = response.json()
    assert body["status"] == 401
    assert body["type"] == _UNAUTHORIZED_TYPE


@pytest.mark.asyncio
async def test_valid_cookie_sets_current_user_id(authed_client: AsyncClient) -> None:
    response = await authed_client.get(
        "/protected", cookies={"access_token": _TOKEN_VALID}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_id"] == SEEDED_USER_UUID


@pytest.mark.asyncio
async def test_expired_token_returns_401(authed_client: AsyncClient) -> None:
    response = await authed_client.get(
        "/protected", cookies={"access_token": _TOKEN_EXPIRED}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_token_without_db_user_returns_401(authed_client: AsyncClient) -> None:
    response = await authed_client.get(
        "/protected", cookies={"access_token": _TOKEN_NO_DB_USER}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["type"] == _UNAUTHORIZED_TYPE


@pytest.mark.asyncio
async def test_header_bypass_blocked_when_session_configured(
    authed_client: AsyncClient,
) -> None:
    response = await authed_client.get(
        "/protected", headers={"X-User-Id": SEEDED_USER_UUID}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_healthz_accessible_without_cookie(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/healthz")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_readyz_accessible_without_cookie(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/readyz")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_no_session_falls_back_to_header(no_session_client: AsyncClient) -> None:
    response = await no_session_client.get(
        "/protected",
        headers={"X-User-Id": SEEDED_USER_UUID},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_id"] == SEEDED_USER_UUID
