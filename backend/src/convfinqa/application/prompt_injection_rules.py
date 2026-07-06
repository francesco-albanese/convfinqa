import re

from convfinqa.application.prompt_injection_types import (
    PromptInjectionAction,
    PromptInjectionFamily,
    PromptInjectionRule,
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

BLOCKING_RULES = (
    PromptInjectionRule(
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
    PromptInjectionRule(
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
    PromptInjectionRule(
        family=PromptInjectionFamily.FAKE_ROLE_DELIMITER,
        reason="fake_role_or_boundary",
        patterns=(
            re.compile(r"(^|\n)\s*(system|developer|assistant|tool)\s*:", re.MULTILINE),
            re.compile(r"<\s*/?\s*(system|developer|assistant|tool|instructions?)\s*>"),
            re.compile(r"```+\s*(system|developer|assistant|tool)\b"),
            re.compile(r'["\']role["\']\s*:\s*["\'](system|developer|tool)["\']'),
        ),
    ),
    PromptInjectionRule(
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
    PromptInjectionRule(
        family=PromptInjectionFamily.MULTILINGUAL_OVERRIDE,
        reason="non_english_override",
        patterns=(
            re.compile(r"\bignora (le )?(istruzioni|regole) (precedenti|precedente)\b"),
            re.compile(r"\bignore (les )?(instructions|regles) precedentes\b"),
            re.compile(
                r"\bignora (las )?(instrucciones|reglas) (anteriores|previas)\b"
            ),
            re.compile(r"تجاهل.{0,40}(التعليمات|القواعد)"),
        ),
    ),
    PromptInjectionRule(
        family=PromptInjectionFamily.REFUSAL_SUPPRESSION,
        reason="refusal_suppression",
        patterns=(
            re.compile(r"\b(do not|don't|never|must not)\b.{0,80}\b(refuse|decline)\b"),
            re.compile(r"\bno refusals?\b|\bwithout refus(ing|al)\b"),
            re.compile(r"\banswer anyway\b|\byou must comply\b"),
        ),
    ),
    PromptInjectionRule(
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

ZERO_WIDTH_RULE = PromptInjectionRule(
    family=PromptInjectionFamily.ZERO_WIDTH_CONTROL,
    reason="zero_width_control",
    patterns=(re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]"),),
    action=PromptInjectionAction.WARN,
)
