from collections.abc import Mapping
from typing import cast

from convfinqa.application.prompt_injection_types import (
    PromptInjectionInput,
    PromptInjectionSurface,
)
from convfinqa.domain.entities import Document


def document_inputs(document: Document) -> tuple[PromptInjectionInput, ...]:
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
    inputs.extend(table_inputs(document.table_data))
    return tuple(inputs)


def table_inputs(table_data: object) -> tuple[PromptInjectionInput, ...]:
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
