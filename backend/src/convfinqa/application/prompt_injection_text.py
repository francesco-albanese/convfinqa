import base64
import binascii
import html
import re
import unicodedata
from collections.abc import Iterable

from convfinqa.application.prompt_injection_rules import (
    BLOCKING_RULES,
    ZERO_WIDTH_RULE,
    ZERO_WIDTH_TRANSLATION,
)
from convfinqa.application.prompt_injection_types import (
    PromptInjectionAction,
    PromptInjectionFamily,
    PromptInjectionFinding,
    PromptInjectionMatchedOn,
    PromptInjectionRule,
    PromptInjectionSurface,
)


def inspect_text(
    text: str, surface: PromptInjectionSurface
) -> tuple[list[PromptInjectionFinding], PromptInjectionAction]:
    findings: list[PromptInjectionFinding] = []
    strongest = PromptInjectionAction.ALLOW

    raw = text or ""
    normalized = normalize(raw)

    zero_width_findings, zero_width_action = apply_rule(
        ZERO_WIDTH_RULE, raw, surface, PromptInjectionMatchedOn.RAW
    )
    findings.extend(zero_width_findings)
    strongest = strongest_action(strongest, zero_width_action)

    for candidate, matched_on in (
        (raw, PromptInjectionMatchedOn.RAW),
        (normalized, PromptInjectionMatchedOn.NORMALIZED),
    ):
        rule_findings, action = apply_blocking_rules(candidate, surface, matched_on)
        findings.extend(rule_findings)
        strongest = strongest_action(strongest, action)

    for decoded in decoded_candidates(raw):
        decoded_findings, decoded_action = apply_blocking_rules(
            normalize(decoded),
            surface,
            PromptInjectionMatchedOn.DECODED,
            family_override=PromptInjectionFamily.ENCODED_PAYLOAD,
            reason_override="encoded_prompt_injection",
        )
        findings.extend(decoded_findings)
        strongest = strongest_action(strongest, decoded_action)

    return findings, strongest


def apply_blocking_rules(
    text: str,
    surface: PromptInjectionSurface,
    matched_on: PromptInjectionMatchedOn,
    family_override: PromptInjectionFamily | None = None,
    reason_override: str | None = None,
) -> tuple[list[PromptInjectionFinding], PromptInjectionAction]:
    findings: list[PromptInjectionFinding] = []
    strongest = PromptInjectionAction.ALLOW

    for rule in BLOCKING_RULES:
        rule_findings, rule_action = apply_rule(
            rule,
            text,
            surface,
            matched_on,
            family_override=family_override,
            reason_override=reason_override,
        )
        findings.extend(rule_findings)
        strongest = strongest_action(strongest, rule_action)

    return findings, strongest


def apply_rule(
    rule: PromptInjectionRule,
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


def normalize(text: str) -> str:
    unescaped = html.unescape(text)
    decomposed = unicodedata.normalize("NFKD", unescaped)
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    without_controls = without_marks.translate(ZERO_WIDTH_TRANSLATION)
    return re.sub(r"\s+", " ", without_controls.casefold()).strip()


def decoded_candidates(text: str) -> tuple[str, ...]:
    candidates: list[str] = []
    tokens = re.findall(r"[A-Za-z0-9+/=]{16,}", text)
    compact = re.sub(r"[^A-Za-z0-9+/=]", "", text)
    if len(compact) >= 16:
        tokens.append(compact)

    for token in tokens:
        decoded = decode_base64(token)
        if decoded is not None:
            candidates.append(decoded)

    for token in re.findall(r"(?:0x)?[0-9A-Fa-f]{24,}", text):
        decoded = decode_hex(token)
        if decoded is not None:
            candidates.append(decoded)

    return tuple(candidates)


def decode_base64(token: str) -> str | None:
    padded = token + ("=" * (-len(token) % 4))
    try:
        raw = base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError):
        return None
    return decode_text(raw)


def decode_hex(token: str) -> str | None:
    value = token[2:] if token.lower().startswith("0x") else token
    if len(value) % 2 != 0:
        return None
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return None
    return decode_text(raw)


def decode_text(raw: bytes) -> str | None:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if not decoded.strip() or printable_ratio(decoded) < 0.75:
        return None
    return decoded


def printable_ratio(text: str) -> float:
    printable = sum(1 for char in text if char.isprintable() or char.isspace())
    return printable / max(len(text), 1)


def dedupe_findings(
    findings: Iterable[PromptInjectionFinding],
) -> tuple[PromptInjectionFinding, ...]:
    return tuple(dict.fromkeys(findings))


def strongest_action(
    left: PromptInjectionAction, right: PromptInjectionAction
) -> PromptInjectionAction:
    order = {
        PromptInjectionAction.ALLOW: 0,
        PromptInjectionAction.OBSERVE: 1,
        PromptInjectionAction.WARN: 2,
        PromptInjectionAction.BLOCK: 3,
    }
    return left if order[left] >= order[right] else right
