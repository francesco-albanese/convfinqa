import re
from dataclasses import dataclass
from enum import StrEnum

PROMPT_INJECTION_REFUSAL = (
    "I can only help with questions grounded in the pinned financial document. "
    "I cannot follow instructions that try to override application rules, reveal "
    "hidden instructions, or change how this assistant operates."
)


class PromptInjectionAction(StrEnum):
    ALLOW = "allow"
    OBSERVE = "observe"
    WARN = "warn"
    BLOCK = "block"


class PromptInjectionFamily(StrEnum):
    DIRECT_OVERRIDE = "direct_override"
    PROMPT_EXTRACTION = "prompt_extraction"
    FAKE_ROLE_DELIMITER = "fake_role_delimiter"
    ENCODED_PAYLOAD = "encoded_payload"
    ZERO_WIDTH_CONTROL = "zero_width_control"
    TYPOGLYCEMIA = "typoglycemia"
    MULTILINGUAL_OVERRIDE = "multilingual_override"
    REFUSAL_SUPPRESSION = "refusal_suppression"
    SAFETY_LABEL_MANIPULATION = "safety_label_manipulation"


class PromptInjectionSurface(StrEnum):
    USER_TEXT = "user_text"
    PRIOR_TURN = "prior_turn"
    DOCUMENT_NARRATIVE = "document_narrative"
    DOCUMENT_METADATA = "document_metadata"
    TABLE_LABEL = "table_label"
    TABLE_VALUE = "table_value"
    TOOL_RESULT = "tool_result"


class PromptInjectionMatchedOn(StrEnum):
    RAW = "raw"
    NORMALIZED = "normalized"
    DECODED = "decoded"


@dataclass(frozen=True, slots=True)
class PromptInjectionFinding:
    family: PromptInjectionFamily
    reason: str
    surface: PromptInjectionSurface
    matched_on: PromptInjectionMatchedOn


@dataclass(frozen=True, slots=True)
class PromptInjectionDecision:
    action: PromptInjectionAction
    findings: tuple[PromptInjectionFinding, ...] = ()

    @property
    def blocked(self) -> bool:
        return self.action == PromptInjectionAction.BLOCK


@dataclass(frozen=True, slots=True)
class PromptInjectionInput:
    text: str
    surface: PromptInjectionSurface


@dataclass(frozen=True, slots=True)
class PromptInjectionRule:
    family: PromptInjectionFamily
    reason: str
    patterns: tuple[re.Pattern[str], ...]
    action: PromptInjectionAction = PromptInjectionAction.BLOCK
