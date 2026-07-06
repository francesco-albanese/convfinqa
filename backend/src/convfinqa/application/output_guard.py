import re
from dataclasses import dataclass
from enum import StrEnum

OUTPUT_GUARD_REFUSAL = (
    "I can’t provide that output. I can help with document-grounded financial "
    "analysis instead."
)


class OutputGuardAction(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"


class OutputGuardReason(StrEnum):
    PROMPT_LEAKAGE = "prompt_leakage"
    TOOL_SCHEMA_LEAKAGE = "tool_schema_leakage"
    REASONING_SIGNATURE_LEAKAGE = "reasoning_signature_leakage"
    SECRET_SHAPED_CONTENT = "secret_shaped_content"
    CROSS_DOCUMENT_CLAIM = "cross_document_claim"
    CITATION_FORGERY = "citation_forgery"
    UNSAFE_MARKUP = "unsafe_markup"


@dataclass(frozen=True, slots=True)
class OutputGuardDecision:
    action: OutputGuardAction
    reason: OutputGuardReason | None = None

    @property
    def blocked(self) -> bool:
        return self.action == OutputGuardAction.BLOCK


@dataclass(frozen=True, slots=True)
class StreamingGuardResult:
    text: str = ""
    blocked: bool = False


class OutputGuard:
    def decide(self, text: str) -> OutputGuardDecision:
        for rule in _RULES:
            if rule.pattern.search(text):
                return OutputGuardDecision(
                    action=OutputGuardAction.BLOCK,
                    reason=rule.reason,
                )
        return OutputGuardDecision(action=OutputGuardAction.ALLOW)


class StreamingOutputGuard:
    def __init__(
        self, guard: OutputGuard | None = None, holdback_chars: int = 96
    ) -> None:
        self._guard = guard or OutputGuard()
        self._holdback_chars = holdback_chars
        self._pending = ""
        self._blocked = False
        self._refusal_emitted = False
        self._reason: OutputGuardReason | None = None

    @property
    def blocked(self) -> bool:
        return self._blocked

    @property
    def reason(self) -> OutputGuardReason | None:
        return self._reason

    def accept(self, text: str) -> StreamingGuardResult:
        if self._blocked:
            return StreamingGuardResult()

        self._pending += text
        decision = self._guard.decide(self._pending)
        if decision.blocked:
            self._blocked = True
            self._reason = decision.reason
            self._pending = ""
            if self._refusal_emitted:
                return StreamingGuardResult(blocked=True)
            self._refusal_emitted = True
            return StreamingGuardResult(text=OUTPUT_GUARD_REFUSAL, blocked=True)

        if len(self._pending) <= self._holdback_chars:
            return StreamingGuardResult()

        emit_length = len(self._pending) - self._holdback_chars
        safe_text = self._pending[:emit_length]
        self._pending = self._pending[emit_length:]
        return StreamingGuardResult(text=safe_text)

    def flush(self) -> StreamingGuardResult:
        if self._blocked:
            return StreamingGuardResult()

        decision = self._guard.decide(self._pending)
        if decision.blocked:
            self._blocked = True
            self._reason = decision.reason
            self._pending = ""
            if self._refusal_emitted:
                return StreamingGuardResult(blocked=True)
            self._refusal_emitted = True
            return StreamingGuardResult(text=OUTPUT_GUARD_REFUSAL, blocked=True)

        safe_text = self._pending
        self._pending = ""
        return StreamingGuardResult(text=safe_text)


@dataclass(frozen=True, slots=True)
class _OutputRule:
    reason: OutputGuardReason
    pattern: re.Pattern[str]


_RULES = (
    _OutputRule(
        OutputGuardReason.PROMPT_LEAKAGE,
        re.compile(
            r"(<trusted_application_policy>|<untrusted_document_context>|"
            r"\b(system|developer) prompt\b|\binternal policy\b)",
            re.IGNORECASE,
        ),
    ),
    _OutputRule(
        OutputGuardReason.TOOL_SCHEMA_LEAKAGE,
        re.compile(
            r"(\btool schemas?\b|\bfunction_call\b|"
            r'"parameters"\s*:\s*\{|"tool_calls"\s*:)',
            re.IGNORECASE,
        ),
    ),
    _OutputRule(
        OutputGuardReason.REASONING_SIGNATURE_LEAKAGE,
        re.compile(
            r'("signature"\s*:|reasoning_signature|thinking_signature)', re.IGNORECASE
        ),
    ),
    _OutputRule(
        OutputGuardReason.SECRET_SHAPED_CONTENT,
        re.compile(
            r"(AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\."
            r"[A-Za-z0-9_-]{10,}|postgres(?:ql)?://|mysql://|redis://|"
            r"Set-Cookie:|session=|/Users/|/aws/lambda/)",
            re.IGNORECASE,
        ),
    ),
    _OutputRule(
        OutputGuardReason.CROSS_DOCUMENT_CLAIM,
        re.compile(
            r"\b(other|another|all|every)\s+(document|filing|conversation)s?\b",
            re.IGNORECASE,
        ),
    ),
    _OutputRule(
        OutputGuardReason.CITATION_FORGERY,
        re.compile(
            r"(data-citation|\"kind\"\s*:\s*\"citation\"|"
            r"\[citation:|<sup[^>]+citation)",
            re.IGNORECASE,
        ),
    ),
    _OutputRule(
        OutputGuardReason.UNSAFE_MARKUP,
        re.compile(
            r"(<\s*(script|iframe|object|embed|img|svg|a)\b|"
            r"\bon\w+\s*=|javascript:|data:text/html|"
            r"!\[[^\]]*\]\(\s*(javascript:|data:)|"
            r"\[[^\]]+\]\(\s*(javascript:|data:text/html))",
            re.IGNORECASE,
        ),
    ),
)
