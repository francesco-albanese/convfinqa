import re
from dataclasses import dataclass
from enum import StrEnum

from convfinqa.domain.entities import Document

DOCUMENT_REFERENCE_TERMS = (
    "document",
    "filing",
    "report",
    "table",
    "row",
    "column",
)
APP_CAPABILITY_PATTERNS = (
    re.compile(r"\bwhat can (you|this app|convfinqa) do\b"),
    re.compile(r"\bhow (do|can) i (use|ask) (you|this app|convfinqa)\b"),
    re.compile(r"\bwhat (questions|kind of questions) can i ask\b"),
    re.compile(r"\bwhat are your capabilities\b"),
)
PROTECTED_INTERNAL_PATTERNS = (
    re.compile(r"\b(system|hidden|developer) prompt\b"),
    re.compile(r"\btool (schema|schemas|definition|definitions|json)\b"),
    re.compile(r"\binternal (policy|policies|instructions|rules)\b"),
)
ROLE_CHANGE_PATTERNS = (
    re.compile(
        r"\b(ignore|override|disregard|forget) (all )?(previous|prior|above) instructions\b"
    ),
    re.compile(r"\bact as\b"),
    re.compile(r"\bpretend (you are|to be)\b"),
    re.compile(r"\byou are now\b"),
    re.compile(r"\breveal (the )?(system|hidden|developer) prompt\b"),
)
CURRENT_PRICE_PATTERNS = (
    re.compile(
        r"\b(current|live|today'?s|latest|real[- ]time)\b.*\b(stock|share) price\b"
    ),
    re.compile(
        r"\b(stock|share) price\b.*\b(current|live|today'?s|latest|real[- ]time)\b"
    ),
)
CROSS_DOCUMENT_PATTERNS = (
    re.compile(
        r"\b(other|another|different|all|every) (document|filing|report|conversation)s?\b"
    ),
    re.compile(
        r"\bcompare\b.*\b(other|another|different|all|every) (document|filing|report)s?\b"
    ),
    re.compile(r"\bnot (the )?pinned document\b"),
)
CODE_REQUEST_PATTERNS = (
    re.compile(
        r"\b(write|generate|create|debug|fix|refactor) "
        r"(some |a |an )?(code|python|javascript|typescript|java|sql)\b"
    ),
    re.compile(
        r"\b(code|python|javascript|typescript|java) (snippet|script|function|program)\b"
    ),
)

PROTECTED_INTERNALS_REASON = "protected_internals"
ROLE_CHANGE_REASON = "role_change"
CROSS_DOCUMENT_REASON = "cross_document"
CURRENT_STOCK_PRICE_REASON = "current_stock_price"
UNRELATED_CODE_REASON = "unrelated_code"
APP_CAPABILITY_REASON = "app_capability"
OFF_DOMAIN_REASON = "off_domain"
DOCUMENT_GROUNDED_REASON = "document_grounded"

REFUSAL = (
    "I can only help with questions grounded in the pinned financial document. "
    "Ask about the document's narrative, table values, or calculations tied to it."
)
APP_CAPABILITY_RESPONSE = (
    "I can answer questions grounded in the pinned financial document, including "
    "summaries, table lookups, comparisons, and calculations. I cannot reveal hidden "
    "instructions, internal policies, or exact tool schemas."
)


class DomainBoundaryAction(StrEnum):
    ALLOW_GENERATION = "allow_generation"
    RESPOND_WITH_POLICY_MESSAGE = "respond_with_policy_message"


@dataclass(frozen=True, slots=True)
class DomainBoundaryDecision:
    action: DomainBoundaryAction
    reason: str
    response: str | None = None


class DomainBoundaryPolicy:
    def decide(self, user_text: str, document: Document) -> DomainBoundaryDecision:
        normalized = _normalize(user_text)

        protected_internal = _matches(normalized, PROTECTED_INTERNAL_PATTERNS)
        if protected_internal:
            return _policy_response(PROTECTED_INTERNALS_REASON)

        if _matches(normalized, ROLE_CHANGE_PATTERNS):
            return _policy_response(ROLE_CHANGE_REASON)

        if _matches(normalized, CROSS_DOCUMENT_PATTERNS):
            return _policy_response(CROSS_DOCUMENT_REASON)

        if _matches(normalized, CURRENT_PRICE_PATTERNS):
            return _policy_response(CURRENT_STOCK_PRICE_REASON)

        if _matches(normalized, CODE_REQUEST_PATTERNS) and not _is_document_grounded(
            normalized, document
        ):
            return _policy_response(UNRELATED_CODE_REASON)

        if _matches(normalized, APP_CAPABILITY_PATTERNS):
            return DomainBoundaryDecision(
                action=DomainBoundaryAction.RESPOND_WITH_POLICY_MESSAGE,
                reason=APP_CAPABILITY_REASON,
                response=APP_CAPABILITY_RESPONSE,
            )

        if _is_document_grounded(normalized, document):
            return DomainBoundaryDecision(
                action=DomainBoundaryAction.ALLOW_GENERATION,
                reason=DOCUMENT_GROUNDED_REASON,
            )

        return _policy_response(OFF_DOMAIN_REASON)


def _policy_response(reason: str) -> DomainBoundaryDecision:
    return DomainBoundaryDecision(
        action=DomainBoundaryAction.RESPOND_WITH_POLICY_MESSAGE,
        reason=reason,
        response=REFUSAL,
    )


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _matches(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) is not None for pattern in patterns)


def _is_document_grounded(text: str, document: Document) -> bool:
    document_terms = {
        str(term).casefold()
        for term in (document.id, document.ticker, document.title, document.year)
        if term not in (None, "") and len(str(term).strip()) >= 2
    }
    has_document_metadata = any(_contains_term(text, term) for term in document_terms)
    has_document_reference = any(
        _contains_term(text, term) for term in DOCUMENT_REFERENCE_TERMS
    )
    return has_document_metadata or has_document_reference


def _contains_term(text: str, term: str) -> bool:
    if re.fullmatch(r"[a-z0-9]+", term) is None:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None
