import base64
import binascii
import html
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from convfinqa.domain.entities import Document, Message

PROMPT_INJECTION_REFUSAL = (
    "I can only help with questions grounded in the pinned financial document. "
    "I cannot follow instructions that try to override application rules, reveal "
    "hidden instructions, or change how this assistant operates."
)

ZERO_WIDTH_TRANSLATION = str.maketrans(
    {
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\u2060": "",
        "\ufeff": "",
    }
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
class _Rule:
    family: PromptInjectionFamily
    reason: str
    patterns: tuple[re.Pattern[str], ...]
    action: PromptInjectionAction = PromptInjectionAction.BLOCK


BLOCKING_RULES = (
    _Rule(
        family=PromptInjectionFamily.DIRECT_OVERRIDE,
        reason="instruction_override",
        patterns=(
            re.compile(
                r"\b(ignore|disregard|forget|bypass|override|discard)\b.{0,80}"
                r"\b(previous|prior|above|earlier|system|developer|application)\b"
                r".{0,80}\b(instruction|instructions|rule|rules|policy|policies)\b"
            ),
            re.compile(
                r"\bnew (system|developer|assistant) instructions?\b|\byou are now\b"
            ),
        ),
    ),
    _Rule(
        family=PromptInjectionFamily.PROMPT_EXTRACTION,
        reason="hidden_prompt_request",
        patterns=(
            re.compile(
                r"\b(print|reveal|show|display|dump|repeat|translate|summarize)\b"
                r".{0,80}\b(system|developer|hidden|initial)\b"
                r".{0,40}\b(prompt|instructions?|message)\b"
            ),
            re.compile(r"\bwhat (is|are) your (system|developer|hidden) prompt"),
        ),
    ),
    _Rule(
        family=PromptInjectionFamily.FAKE_ROLE_DELIMITER,
        reason="fake_role_or_boundary",
        patterns=(
            re.compile(r"(^|\n)\s*(system|developer|assistant|tool)\s*:", re.MULTILINE),
            re.compile(r"<\s*/?\s*(system|developer|assistant|tool|instructions?)\s*>"),
            re.compile(r"```+\s*(system|developer|assistant|tool)\b"),
            re.compile(r'["\']role["\']\s*:\s*["\'](system|developer|tool)["\']'),
        ),
    ),
    _Rule(
        family=PromptInjectionFamily.TYPOGLYCEMIA,
        reason="misspelled_override",
        patterns=(
            re.compile(r"\bignroe\b|\bdsi?regard\b|\bovverride\b|\bprevoius\b"),
            re.compile(
                r"\bign\w{1,4}re\b.{0,60}"
                r"\b(prev\w{2,8}|instr\w{3,8}|rules?)\b"
            ),
        ),
    ),
    _Rule(
        family=PromptInjectionFamily.MULTILINGUAL_OVERRIDE,
        reason="non_english_override",
        patterns=(
            re.compile(
                r"\bignora (le )?(istruzioni|regole) (precedenti|precedente)\b"
            ),
            re.compile(r"\bignore (les )?(instructions|regles) precedentes\b"),
            re.compile(
                r"\bignora (las )?(instrucciones|reglas) (anteriores|previas)\b"
            ),
            re.compile(r"تجاهل.{0,40}(التعليمات|القواعد)"),
        ),
    ),
    _Rule(
        family=PromptInjectionFamily.REFUSAL_SUPPRESSION,
        reason="refusal_suppression",
        patterns=(
            re.compile(r"\b(do not|don't|never|must not)\b.{0,80}\b(refuse|decline)\b"),
            re.compile(r"\bno refusals?\b|\bwithout refus(ing|al)\b"),
            re.compile(r"\banswer anyway\b|\byou must comply\b"),
        ),
    ),
    _Rule(
        family=PromptInjectionFamily.SAFETY_LABEL_MANIPULATION,
        reason="safety_label_manipulation",
        patterns=(
            re.compile(
                r"\b(classify|mark|marked|treat)\b.{0,40}"
                r"\b(this|message|request|prompt|input)\b.{0,40}"
                r"\b(safe|trusted|benign)\b"
            ),
            re.compile(
                r"\b(this is an? )?(authorized|trusted)\b.{0,20}"
                r"\b(security audit|red[- ]team|jailbreak test)\b"
            ),
            re.compile(
                r"\b(developer mode|jailbreak|admin mode|god mode|authorized test)\b"
            ),
        ),
    ),
)

ZERO_WIDTH_RULE = _Rule(
    family=PromptInjectionFamily.ZERO_WIDTH_CONTROL,
    reason="zero_width_control",
    patterns=(re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]"),),
    action=PromptInjectionAction.WARN,
)


class PromptInjectionDetector:
    def decide(
        self,
        text: str,
        surface: PromptInjectionSurface = PromptInjectionSurface.USER_TEXT,
    ) -> PromptInjectionDecision:
        return self.decide_many((PromptInjectionInput(text=text, surface=surface),))

    def decide_many(
        self, inputs: Iterable[PromptInjectionInput]
    ) -> PromptInjectionDecision:
        findings: list[PromptInjectionFinding] = []
        strongest = PromptInjectionAction.ALLOW

        for item in inputs:
            item_findings, item_action = _inspect_text(item.text, item.surface)
            findings.extend(item_findings)
            strongest = _strongest_action(strongest, item_action)

        return PromptInjectionDecision(
            action=strongest,
            findings=_dedupe_findings(findings),
        )

    def decide_document(self, document: Document) -> PromptInjectionDecision:
        return self.decide_many(_document_inputs(document))

    def decide_prior_turns(self, messages: Iterable[Message]) -> PromptInjectionDecision:
        return self.decide_many(
            PromptInjectionInput(
                text=message.content,
                surface=PromptInjectionSurface.PRIOR_TURN,
            )
            for message in messages
        )


def _inspect_text(
    text: str, surface: PromptInjectionSurface
) -> tuple[list[PromptInjectionFinding], PromptInjectionAction]:
    findings: list[PromptInjectionFinding] = []
    strongest = PromptInjectionAction.ALLOW

    raw = text or ""
    normalized = _normalize(raw)

    zero_width_findings, zero_width_action = _apply_rule(
        ZERO_WIDTH_RULE, raw, surface, PromptInjectionMatchedOn.RAW
    )
    findings.extend(zero_width_findings)
    strongest = _strongest_action(strongest, zero_width_action)

    for candidate, matched_on in (
        (raw, PromptInjectionMatchedOn.RAW),
        (normalized, PromptInjectionMatchedOn.NORMALIZED),
    ):
        rule_findings, action = _apply_blocking_rules(candidate, surface, matched_on)
        findings.extend(rule_findings)
        strongest = _strongest_action(strongest, action)

    for decoded in _decoded_candidates(raw):
        decoded_findings, decoded_action = _apply_blocking_rules(
            _normalize(decoded),
            surface,
            PromptInjectionMatchedOn.DECODED,
            family_override=PromptInjectionFamily.ENCODED_PAYLOAD,
            reason_override="encoded_prompt_injection",
        )
        findings.extend(decoded_findings)
        strongest = _strongest_action(strongest, decoded_action)

    return findings, strongest


def _apply_blocking_rules(
    text: str,
    surface: PromptInjectionSurface,
    matched_on: PromptInjectionMatchedOn,
    family_override: PromptInjectionFamily | None = None,
    reason_override: str | None = None,
) -> tuple[list[PromptInjectionFinding], PromptInjectionAction]:
    findings: list[PromptInjectionFinding] = []
    strongest = PromptInjectionAction.ALLOW

    for rule in BLOCKING_RULES:
        rule_findings, rule_action = _apply_rule(
            rule,
            text,
            surface,
            matched_on,
            family_override=family_override,
            reason_override=reason_override,
        )
        findings.extend(rule_findings)
        strongest = _strongest_action(strongest, rule_action)

    return findings, strongest


def _apply_rule(
    rule: _Rule,
    text: str,
    surface: PromptInjectionSurface,
    matched_on: PromptInjectionMatchedOn,
    family_override: PromptInjectionFamily | None = None,
    reason_override: str | None = None,
) -> tuple[list[PromptInjectionFinding], PromptInjectionAction]:
    if text == "":
        return [], PromptInjectionAction.ALLOW

    findings = [
        PromptInjectionFinding(
            family=family_override or rule.family,
            reason=reason_override or rule.reason,
            surface=surface,
            matched_on=matched_on,
        )
        for pattern in rule.patterns
        if pattern.search(text) is not None
    ]
    if not findings:
        return [], PromptInjectionAction.ALLOW
    return findings, rule.action


def _normalize(text: str) -> str:
    unescaped = html.unescape(text)
    decomposed = unicodedata.normalize("NFKD", unescaped)
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    without_controls = without_marks.translate(ZERO_WIDTH_TRANSLATION)
    return re.sub(r"\s+", " ", without_controls.casefold()).strip()


def _decoded_candidates(text: str) -> tuple[str, ...]:
    candidates: list[str] = []
    tokens = re.findall(r"[A-Za-z0-9+/=]{16,}", text)
    compact = re.sub(r"[^A-Za-z0-9+/=]", "", text)
    if len(compact) >= 16:
        tokens.append(compact)

    for token in tokens:
        decoded = _decode_base64(token)
        if decoded is not None:
            candidates.append(decoded)

    for token in re.findall(r"(?:0x)?[0-9A-Fa-f]{24,}", text):
        decoded = _decode_hex(token)
        if decoded is not None:
            candidates.append(decoded)

    return tuple(candidates)


def _decode_base64(token: str) -> str | None:
    padded = token + ("=" * (-len(token) % 4))
    try:
        raw = base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError):
        return None
    return _decode_text(raw)


def _decode_hex(token: str) -> str | None:
    value = token[2:] if token.lower().startswith("0x") else token
    if len(value) % 2 != 0:
        return None
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return None
    return _decode_text(raw)


def _decode_text(raw: bytes) -> str | None:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not decoded.strip() or _printable_ratio(decoded) < 0.75:
        return None
    return decoded


def _printable_ratio(text: str) -> float:
    printable = sum(1 for char in text if char.isprintable() or char.isspace())
    return printable / max(len(text), 1)


def _document_inputs(document: Document) -> tuple[PromptInjectionInput, ...]:
    inputs = [
        PromptInjectionInput(
            text=str(value),
            surface=PromptInjectionSurface.DOCUMENT_METADATA,
        )
        for value in (
            document.id,
            document.ticker,
            document.year,
            document.page,
            document.title,
        )
        if value not in (None, "")
    ]
    for value in (document.pre_text, document.post_text):
        if value:
            inputs.append(
                PromptInjectionInput(
                    text=value,
                    surface=PromptInjectionSurface.DOCUMENT_NARRATIVE,
                )
            )
    inputs.extend(_table_inputs(document.table_data))
    return tuple(inputs)


def _table_inputs(table_data: object) -> tuple[PromptInjectionInput, ...]:
    inputs: list[PromptInjectionInput] = []

    def walk(value: object) -> None:
        if isinstance(value, Mapping):
            typed_mapping = cast(Mapping[object, object], value)
            for key, nested in typed_mapping.items():
                inputs.append(
                    PromptInjectionInput(
                        text=str(key),
                        surface=PromptInjectionSurface.TABLE_LABEL,
                    )
                )
                walk(nested)
            return

        if isinstance(value, list | tuple):
            typed_sequence = cast(list[object] | tuple[object, ...], value)
            for item in typed_sequence:
                walk(item)
            return

        if value not in (None, ""):
            inputs.append(
                PromptInjectionInput(
                    text=str(value),
                    surface=PromptInjectionSurface.TABLE_VALUE,
                )
            )

    walk(table_data)
    return tuple(inputs)


def _dedupe_findings(
    findings: Iterable[PromptInjectionFinding],
) -> tuple[PromptInjectionFinding, ...]:
    return tuple(dict.fromkeys(findings))


def _strongest_action(
    left: PromptInjectionAction, right: PromptInjectionAction
) -> PromptInjectionAction:
    order = {
        PromptInjectionAction.ALLOW: 0,
        PromptInjectionAction.OBSERVE: 1,
        PromptInjectionAction.WARN: 2,
        PromptInjectionAction.BLOCK: 3,
    }
    return left if order[left] >= order[right] else right
