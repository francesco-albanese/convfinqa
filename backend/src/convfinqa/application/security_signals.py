import logging
from collections.abc import Iterable

from convfinqa.logging import get_logger

SECURITY_LOGGER_NAME = "convfinqa.security"

DOMAIN_BOUNDARY_BLOCKED = "domain_boundary_blocked"
PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
TOOL_POLICY_BLOCKED = "tool_policy_blocked"
OUTPUT_GUARD_BLOCKED = "output_guard_blocked"
PROVIDER_THROTTLED = "provider_throttled"
COST_CONTROL_TRIGGERED = "cost_control_triggered"
SUSPICIOUS_ACTIVITY_THROTTLED = "suspicious_activity_throttled"
SECURITY_REGRESSION_FAILED = "security_regression_failed"

RATE_LIMITED = "rate_limited"
BUDGET_EXCEEDED = "budget_exceeded"
CONTEXT_WINDOW_EXCEEDED = "context_window_exceeded"


def classify_provider_error(exc: BaseException) -> str | None:
    name = exc.__class__.__name__.casefold()
    status_code = getattr(exc, "status_code", None)
    # litellm's BudgetExceededError also carries status_code=429, so the
    # budget check must run before the generic 429/rate-limit catch-all.
    if "budget" in name:
        return BUDGET_EXCEEDED
    if "contextwindow" in name:
        return CONTEXT_WINDOW_EXCEEDED
    if status_code == 429 or "ratelimit" in name or "throttl" in name:
        return RATE_LIMITED
    return None


class SecuritySignals:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or get_logger(SECURITY_LOGGER_NAME)

    def domain_boundary_blocked(
        self,
        *,
        conversation_id: str,
        document_id: str,
        model: str,
        reason: str,
    ) -> None:
        self._emit(
            DOMAIN_BOUNDARY_BLOCKED,
            conversation_id=conversation_id,
            document_id=document_id,
            model=model,
            reason=reason,
        )

    def prompt_injection_detected(
        self,
        *,
        conversation_id: str,
        document_id: str,
        model: str,
        action: str,
        families: Iterable[str],
        surfaces: Iterable[str],
        detector_failed: bool = False,
    ) -> None:
        self._emit(
            PROMPT_INJECTION_DETECTED,
            conversation_id=conversation_id,
            document_id=document_id,
            model=model,
            action=action,
            families=sorted(set(families)),
            surfaces=sorted(set(surfaces)),
            detector_failed=detector_failed,
        )

    def tool_policy_blocked(
        self,
        *,
        conversation_id: str,
        document_id: str,
        tool_name: str,
        reason: str,
    ) -> None:
        self._emit(
            TOOL_POLICY_BLOCKED,
            conversation_id=conversation_id,
            document_id=document_id,
            tool_name=tool_name,
            reason=reason,
        )

    def output_guard_blocked(
        self,
        *,
        conversation_id: str,
        document_id: str,
        model: str,
        reason: str,
    ) -> None:
        self._emit(
            OUTPUT_GUARD_BLOCKED,
            conversation_id=conversation_id,
            document_id=document_id,
            model=model,
            reason=reason,
        )

    def provider_throttled(
        self,
        *,
        conversation_id: str,
        model: str,
        condition: str,
        exc_type: str,
    ) -> None:
        self._emit(
            PROVIDER_THROTTLED,
            conversation_id=conversation_id,
            model=model,
            condition=condition,
            exc_type=exc_type,
        )

    def cost_control_triggered(
        self,
        *,
        conversation_id: str,
        model: str,
        control: str,
    ) -> None:
        self._emit(
            COST_CONTROL_TRIGGERED,
            conversation_id=conversation_id,
            model=model,
            control=control,
        )

    def suspicious_activity_throttled(
        self,
        *,
        conversation_id: str,
        attempts: int,
        window_seconds: int,
    ) -> None:
        self._emit(
            SUSPICIOUS_ACTIVITY_THROTTLED,
            conversation_id=conversation_id,
            attempts=attempts,
            window_seconds=window_seconds,
        )

    def security_regression_failed(
        self,
        *,
        suite: str,
        attack_family: str,
        detail: str,
    ) -> None:
        self._emit(
            SECURITY_REGRESSION_FAILED,
            suite=suite,
            attack_family=attack_family,
            detail=detail,
        )

    def _emit(self, event: str, **fields: object) -> None:
        self._logger.warning(event, extra={"security_event": event, **fields})
