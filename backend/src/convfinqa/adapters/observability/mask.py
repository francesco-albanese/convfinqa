import re
from typing import Any, cast

JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$")
CREDENTIAL_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "secret",
        "password",
        "token",
        "user_text",
        "aws_session_token",
        "aws_secret_access_key",
        "private_key",
    }
)
SENSITIVE_HEADER_KEYS = frozenset({"authorization", "cookie", "set-cookie"})

REDACTED = "[REDACTED]"


def mask(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return _mask_string(value)
    if isinstance(value, dict):
        return _mask_dict(cast(dict[str, Any], value))
    if isinstance(value, list):
        return [mask(item) for item in cast(list[Any], value)]
    return value


def _mask_string(value: str) -> str:
    if JWT_RE.match(value):
        return REDACTED
    return value


def _mask_dict(d: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, val in d.items():
        lower_key = key.lower()
        if lower_key in SENSITIVE_HEADER_KEYS:
            result[key] = REDACTED
        elif lower_key in CREDENTIAL_KEYS:
            result[key] = REDACTED
        else:
            result[key] = mask(val)
    return result
