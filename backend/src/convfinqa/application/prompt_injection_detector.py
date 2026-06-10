from collections.abc import Iterable

from convfinqa.application.prompt_injection_document import document_inputs
from convfinqa.application.prompt_injection_text import (
    dedupe_findings,
    inspect_text,
    strongest_action,
)
from convfinqa.application.prompt_injection_types import (
    PROMPT_INJECTION_REFUSAL,
    PromptInjectionAction,
    PromptInjectionDecision,
    PromptInjectionFamily,
    PromptInjectionFinding,
    PromptInjectionInput,
    PromptInjectionMatchedOn,
    PromptInjectionSurface,
)
from convfinqa.domain.entities import Document, Message


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
            item_findings, item_action = inspect_text(item.text, item.surface)
            findings.extend(item_findings)
            strongest = strongest_action(strongest, item_action)

        return PromptInjectionDecision(
            action=strongest,
            findings=dedupe_findings(findings),
        )

    def decide_document(self, document: Document) -> PromptInjectionDecision:
        return self.decide_many(document_inputs(document))

    def decide_prior_turns(
        self, messages: Iterable[Message]
    ) -> PromptInjectionDecision:
        return self.decide_many(
            PromptInjectionInput(
                text=message.content,
                surface=PromptInjectionSurface.PRIOR_TURN,
            )
            for message in messages
        )


__all__ = [
    "PROMPT_INJECTION_REFUSAL",
    "PromptInjectionAction",
    "PromptInjectionDecision",
    "PromptInjectionDetector",
    "PromptInjectionFamily",
    "PromptInjectionFinding",
    "PromptInjectionInput",
    "PromptInjectionMatchedOn",
    "PromptInjectionSurface",
]
