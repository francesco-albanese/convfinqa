from dataclasses import dataclass
from typing import Protocol


class SessionVerificationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedClaims:
    sub: str
    exp: int
    email: str | None = None


class SessionPort(Protocol):
    async def verify_access_token(self, token: str) -> ValidatedClaims: ...
