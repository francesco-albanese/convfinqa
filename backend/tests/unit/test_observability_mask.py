import pytest

from convfinqa.adapters.observability.mask import REDACTED, mask


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("plain text no redaction needed", "plain text no redaction needed"),
        (-2913, -2913),
        (42, 42),
        (3.14, 3.14),
        (
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.abc123def",
            REDACTED,
        ),
        (
            {"authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.abc"},
            {"authorization": REDACTED},
        ),
        (
            {"Authorization": "token"},
            {"Authorization": REDACTED},
        ),
        (
            {"cookie": "session=abc"},
            {"cookie": REDACTED},
        ),
        (
            {"set-cookie": "session=xyz; HttpOnly"},
            {"set-cookie": REDACTED},
        ),
        (
            {"api_key": "sk-1234"},
            {"api_key": REDACTED},
        ),
        (
            {"password": "hunter2"},
            {"password": REDACTED},
        ),
        (
            {"aws_session_token": "ASIA..."},
            {"aws_session_token": REDACTED},
        ),
        (
            {"aws_secret_access_key": "wJalrXUtnFEMI"},
            {"aws_secret_access_key": REDACTED},
        ),
        (
            {"private_key": "-----BEGIN RSA PRIVATE KEY-----"},
            {"private_key": REDACTED},
        ),
        (
            {"token": "FAKE_TOKEN_PLACEHOLDER"},
            {"token": REDACTED},
        ),
        (
            {"question": "What was revenue in 2023?", "document_id": "acme/2023.pdf"},
            {"question": "What was revenue in 2023?", "document_id": "acme/2023.pdf"},
        ),
        (
            {"nested": {"api_key": "secret", "safe": "value"}},
            {"nested": {"api_key": REDACTED, "safe": "value"}},
        ),
        (
            [{"password": "x"}, "plain", None, 99],
            [{"password": REDACTED}, "plain", None, 99],
        ),
        (
            {"user_text": "What is the revenue?"},
            {"user_text": REDACTED},
        ),
    ],
)
def test_mask(value: object, expected: object) -> None:
    assert mask(value) == expected
