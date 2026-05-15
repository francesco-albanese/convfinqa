import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Final

import httpx
import jwt
from cachetools import TTLCache
from jwt.algorithms import RSAAlgorithm

from convfinqa.domain.ports.session import SessionVerificationError, ValidatedClaims

_CACHE_MAXSIZE: Final = 10_000
_CACHE_TTL_SECONDS: Final[float] = 300.0


async def _default_fetch_jwks(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


@dataclass(slots=True)
class CognitoJwksAdapter:
    jwks_url: str
    issuer: str
    client_id: str
    fetch_jwks: Callable[[str], Awaitable[dict[str, Any]]] = field(
        default=_default_fetch_jwks
    )
    find_user_by_sub: Callable[[str], Awaitable[uuid.UUID | None]] | None = None
    cache_ttl_seconds: float = _CACHE_TTL_SECONDS
    _keys: dict[str, Any] = field(default_factory=dict, init=False, repr=False)  # pyright: ignore[reportUnknownVariableType]
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    _user_cache: TTLCache[str, uuid.UUID | None] = field(  # pyright: ignore[reportUnknownVariableType,reportAssignmentType]
        default_factory=lambda: TTLCache(maxsize=_CACHE_MAXSIZE, ttl=_CACHE_TTL_SECONDS),
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._user_cache = TTLCache(maxsize=_CACHE_MAXSIZE, ttl=self.cache_ttl_seconds)  # pyright: ignore[reportAttributeAccessIssue]

    async def _ensure_keys(self) -> None:
        if self._keys:
            return
        async with self._lock:
            if self._keys:
                return
            data = await self.fetch_jwks(self.jwks_url)
            self._keys = {
                jwk["kid"]: RSAAlgorithm.from_jwk(jwk)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
                for jwk in data["keys"]
            }

    async def _resolve_user_id(self, sub: str) -> uuid.UUID | None:
        if self.find_user_by_sub is None:
            return None
        try:
            return self._user_cache[sub]
        except KeyError:
            user_id = await self.find_user_by_sub(sub)
            self._user_cache[sub] = user_id
            return user_id

    async def verify_access_token(self, token: str) -> ValidatedClaims:
        await self._ensure_keys()
        try:
            header = jwt.get_unverified_header(token)
            kid: str = header.get("kid", "")
            if kid not in self._keys:
                raise SessionVerificationError(f"Unknown key ID: {kid}")
            payload: dict[str, Any] = jwt.decode(
                token,
                self._keys[kid],
                algorithms=["RS256"],
                issuer=self.issuer,
                options={"verify_aud": False},
            )
            if payload.get("token_use") != "access":
                raise SessionVerificationError("Not an access token")
            if payload.get("client_id") != self.client_id:
                raise SessionVerificationError("Invalid client_id")
            sub = str(payload["sub"])
            user_id = await self._resolve_user_id(sub)
            return ValidatedClaims(
                sub=sub,
                exp=int(payload["exp"]),
                email=str(payload["email"]) if payload.get("email") else None,
                user_id=user_id,
            )
        except jwt.ExpiredSignatureError as exc:
            raise SessionVerificationError("Token expired") from exc
        except jwt.InvalidIssuerError as exc:
            raise SessionVerificationError("Invalid issuer") from exc
        except jwt.DecodeError as exc:
            raise SessionVerificationError("Invalid token signature") from exc
        except jwt.InvalidTokenError as exc:
            raise SessionVerificationError(str(exc)) from exc
