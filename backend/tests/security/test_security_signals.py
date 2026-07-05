import logging

import pytest

from convfinqa.application.security_signals import (
    BUDGET_EXCEEDED,
    CONTEXT_WINDOW_EXCEEDED,
    PROMPT_INJECTION_DETECTED,
    RATE_LIMITED,
    SECURITY_LOGGER_NAME,
    SecuritySignals,
    classify_provider_error,
)


class FakeRateLimitError(Exception):
    status_code = 429


class ThrottlingException(Exception):  # noqa: N818 - mirrors the real AWS Bedrock exception name
    pass


class BudgetExceededError(Exception):
    pass


class ContextWindowExceededError(Exception):
    pass


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (FakeRateLimitError("slow down"), RATE_LIMITED),
        (ThrottlingException("bedrock throttle"), RATE_LIMITED),
        (BudgetExceededError("cap hit"), BUDGET_EXCEEDED),
        (ContextWindowExceededError("too long"), CONTEXT_WINDOW_EXCEEDED),
        (ValueError("unrelated"), None),
    ],
)
def test_classify_provider_error(exc: Exception, expected: str | None) -> None:
    assert classify_provider_error(exc) == expected


def test_prompt_injection_signal_has_stable_name_and_safe_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    signals = SecuritySignals()

    with caplog.at_level(logging.WARNING, logger=SECURITY_LOGGER_NAME):
        signals.prompt_injection_detected(
            conversation_id="conv-1",
            document_id="doc-1",
            model="test-model",
            action="block",
            families=("direct_override", "direct_override", "encoded_payload"),
            surfaces=("user_text",),
        )

    record = caplog.records[0]
    assert record.getMessage() == PROMPT_INJECTION_DETECTED
    assert record.security_event == PROMPT_INJECTION_DETECTED  # type: ignore[attr-defined]
    assert record.conversation_id == "conv-1"  # type: ignore[attr-defined]
    assert record.families == ["direct_override", "encoded_payload"]  # type: ignore[attr-defined]
    assert record.surfaces == ["user_text"]  # type: ignore[attr-defined]


def test_signals_use_injected_logger(caplog: pytest.LogCaptureFixture) -> None:
    custom = logging.getLogger("test.custom.security")
    signals = SecuritySignals(logger=custom)

    with caplog.at_level(logging.WARNING, logger="test.custom.security"):
        signals.suspicious_activity_throttled(
            conversation_id="conv-2", attempts=7, window_seconds=300
        )

    record = caplog.records[0]
    assert record.name == "test.custom.security"
    assert record.attempts == 7  # type: ignore[attr-defined]
