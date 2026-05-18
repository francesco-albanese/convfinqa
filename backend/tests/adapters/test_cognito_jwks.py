"""Tests for CognitoJwksAdapter — all unit tests (no network, no DB)."""

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from convfinqa.adapters.auth.cognito_jwks import CognitoJwksAdapter
from convfinqa.domain.ports.session import SessionVerificationError, UserRecord

pytestmark = pytest.mark.unit

_REGION = "eu-west-1"
_POOL_ID = "eu-west-1_TestPool"
_CLIENT_ID = "test-client-id"
_ISSUER = f"https://cognito-idp.{_REGION}.amazonaws.com/{_POOL_ID}"
_KID = "test-key-1"


def _generate_rsa_key_pair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _build_jwks(public_key: rsa.RSAPublicKey) -> dict[str, Any]:
    jwk: dict[str, Any] = RSAAlgorithm.to_jwk(public_key, as_dict=True)  # type: ignore[no-untyped-call]
    jwk["kid"] = _KID
    return {"keys": [jwk]}


def _mint_token(
    private_key: rsa.RSAPrivateKey,
    *,
    sub: str = "user-sub-123",
    email: str | None = None,
    exp_offset: int = 3600,
    issuer: str = _ISSUER,
    client_id: str = _CLIENT_ID,
    token_use: str = "access",
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": sub,
        "iss": issuer,
        "client_id": client_id,
        "token_use": token_use,
        "iat": now,
        "exp": now + exp_offset,
    }
    if email is not None:
        claims["email"] = email
    return jwt.encode(
        claims,
        private_key,  # type: ignore[arg-type]
        algorithm="RS256",
        headers={"kid": _KID},
    )


def _make_adapter(
    fetch_mock: Callable[[str], Awaitable[dict[str, Any]]],
) -> CognitoJwksAdapter:
    return CognitoJwksAdapter(
        jwks_url=f"https://cognito-idp.{_REGION}.amazonaws.com/{_POOL_ID}/.well-known/jwks.json",
        issuer=_ISSUER,
        client_id=_CLIENT_ID,
        fetch_jwks=fetch_mock,
    )


@pytest.fixture()
def rsa_keys() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    return _generate_rsa_key_pair()


@pytest.fixture()
def fetch_mock(
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> AsyncMock:
    _, public_key = rsa_keys
    jwks = _build_jwks(public_key)
    mock = AsyncMock(return_value=jwks)
    return mock


@pytest.fixture()
def adapter(fetch_mock: AsyncMock) -> CognitoJwksAdapter:
    return _make_adapter(fetch_mock)


async def test_valid_token_returns_claims(
    adapter: CognitoJwksAdapter,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    token = _mint_token(private_key, sub="abc-123")

    claims = await adapter.verify_access_token(token)

    assert claims.sub == "abc-123"
    assert claims.email is None
    assert claims.exp > int(time.time())


async def test_expired_token_raises(
    adapter: CognitoJwksAdapter,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    token = _mint_token(private_key, exp_offset=-1)

    with pytest.raises(SessionVerificationError, match="expired"):
        await adapter.verify_access_token(token)


async def test_wrong_issuer_raises(
    adapter: CognitoJwksAdapter,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    token = _mint_token(private_key, issuer="https://evil.example.com/pool")

    with pytest.raises(SessionVerificationError, match="issuer"):
        await adapter.verify_access_token(token)


async def test_wrong_client_id_raises(
    adapter: CognitoJwksAdapter,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    token = _mint_token(private_key, client_id="wrong-client-id")

    with pytest.raises(SessionVerificationError, match="client_id"):
        await adapter.verify_access_token(token)


async def test_bad_signature_raises(
    adapter: CognitoJwksAdapter,
) -> None:
    other_private, _ = _generate_rsa_key_pair()
    token = _mint_token(other_private)

    with pytest.raises(SessionVerificationError, match="signature"):
        await adapter.verify_access_token(token)


async def test_id_token_use_rejected(
    adapter: CognitoJwksAdapter,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    token = _mint_token(private_key, token_use="id")

    with pytest.raises(SessionVerificationError, match="Not an access token"):
        await adapter.verify_access_token(token)


async def test_unknown_kid_raises(
    fetch_mock: AsyncMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    unknown_kid = "unknown-key-999"
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "s",
            "iss": _ISSUER,
            "client_id": _CLIENT_ID,
            "token_use": "access",
            "iat": now,
            "exp": now + 3600,
        },
        private_key,  # type: ignore[arg-type]
        algorithm="RS256",
        headers={"kid": unknown_kid},
    )

    with pytest.raises(
        SessionVerificationError, match=f"Unknown key ID: {unknown_kid}"
    ):
        await _make_adapter(fetch_mock).verify_access_token(token)


async def test_jwks_fetched_once_across_multiple_verifications(
    adapter: CognitoJwksAdapter,
    fetch_mock: AsyncMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    token = _mint_token(private_key)

    await adapter.verify_access_token(token)
    await adapter.verify_access_token(token)

    fetch_mock.assert_called_once()


def _make_adapter_with_lookup(
    fetch_mock: Callable[[str], Awaitable[dict[str, Any]]],
    find_user: AsyncMock,
    cache_ttl_seconds: float = 300.0,
) -> CognitoJwksAdapter:
    return CognitoJwksAdapter(
        jwks_url=f"https://cognito-idp.{_REGION}.amazonaws.com/{_POOL_ID}/.well-known/jwks.json",
        issuer=_ISSUER,
        client_id=_CLIENT_ID,
        fetch_jwks=fetch_mock,
        find_user_by_sub=find_user,
        cache_ttl_seconds=cache_ttl_seconds,
    )


async def test_user_id_is_none_without_lookup(
    adapter: CognitoJwksAdapter,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    private_key, _ = rsa_keys
    token = _mint_token(private_key)

    claims = await adapter.verify_access_token(token)

    assert claims.user_id is None


async def test_user_id_and_email_resolved_from_db(
    fetch_mock: AsyncMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    expected = UserRecord(user_id=uuid.uuid4(), email="user@example.com")
    find_user = AsyncMock(return_value=expected)
    adapter = _make_adapter_with_lookup(fetch_mock, find_user)
    private_key, _ = rsa_keys
    token = _mint_token(private_key, sub="user-sub-123")

    claims = await adapter.verify_access_token(token)

    assert claims.user_id == expected.user_id
    assert claims.email == "user@example.com"
    find_user.assert_called_once_with("user-sub-123")


async def test_email_comes_from_db_not_jwt_claim(
    fetch_mock: AsyncMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    expected = UserRecord(user_id=uuid.uuid4(), email="db@example.com")
    find_user = AsyncMock(return_value=expected)
    adapter = _make_adapter_with_lookup(fetch_mock, find_user)
    private_key, _ = rsa_keys
    token = _mint_token(private_key, sub="user-sub-123", email="jwt@example.com")

    claims = await adapter.verify_access_token(token)

    assert claims.email == "db@example.com"


async def test_cache_hit_avoids_second_db_lookup(
    fetch_mock: AsyncMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    expected = UserRecord(user_id=uuid.uuid4(), email="user@example.com")
    find_user = AsyncMock(return_value=expected)
    adapter = _make_adapter_with_lookup(fetch_mock, find_user)
    private_key, _ = rsa_keys
    token = _mint_token(private_key, sub="abc-123")

    await adapter.verify_access_token(token)
    claims = await adapter.verify_access_token(token)

    assert claims.user_id == expected.user_id
    find_user.assert_called_once()


async def test_db_miss_returns_none_user_id(
    fetch_mock: AsyncMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    find_user = AsyncMock(return_value=None)
    adapter = _make_adapter_with_lookup(fetch_mock, find_user)
    private_key, _ = rsa_keys
    token = _mint_token(private_key, sub="unknown-sub")

    claims = await adapter.verify_access_token(token)

    assert claims.user_id is None
    assert claims.email is None


async def test_ttl_expiry_triggers_relookup(
    fetch_mock: AsyncMock,
    rsa_keys: tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey],
) -> None:
    expected = UserRecord(user_id=uuid.uuid4(), email="user@example.com")
    find_user = AsyncMock(return_value=expected)
    adapter = _make_adapter_with_lookup(fetch_mock, find_user, cache_ttl_seconds=0.05)
    private_key, _ = rsa_keys
    token = _mint_token(private_key, sub="ttl-test-sub")

    await adapter.verify_access_token(token)
    await asyncio.sleep(0.2)
    await adapter.verify_access_token(token)

    assert find_user.call_count == 2
