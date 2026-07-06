from dataclasses import dataclass, field
from typing import Any

import pytest

from convfinqa.adapters.prompts.langfuse_provider import LangfusePromptProvider


@dataclass
class FakePrompt:
    prompt: str
    version: int = 3
    config: dict[str, Any] = field(default_factory=dict[str, Any])


@dataclass
class FakeClient:
    prompt: str
    seen_labels: list[str] | None = None
    config: dict[str, Any] = field(default_factory=dict[str, Any])

    def get_prompt(
        self, name: str, *, label: str, type: str, cache_ttl_seconds: int
    ) -> FakePrompt:
        if self.seen_labels is not None:
            self.seen_labels.append(label)
        return FakePrompt(prompt=self.prompt, config=self.config)


async def test_fetches_by_label_and_compiles_variables() -> None:
    seen_labels: list[str] = []
    client = FakeClient(prompt="Hello {{name}}.", seen_labels=seen_labels)
    provider = LangfusePromptProvider(client)

    compiled = await provider.compile("convfinqa-system", "production", {"name": "X"})

    assert compiled.text == "Hello X."
    assert compiled.version == 3
    assert seen_labels == ["production"]


async def test_exposes_the_prompts_config_for_ab_selection() -> None:
    client = FakeClient(prompt="Hello {{name}}.", config={"ab": {"enabled": True}})
    provider = LangfusePromptProvider(client)

    compiled = await provider.compile("convfinqa-system", "production", {"name": "X"})

    assert compiled.config == {"ab": {"enabled": True}}


async def test_raises_on_missing_variable_matching_local_provider_strictness() -> None:
    client = FakeClient(prompt="Hello {{name}}.")
    provider = LangfusePromptProvider(client)

    with pytest.raises(ValueError, match="missing prompt variable: name"):
        await provider.compile("convfinqa-system", "production", {})


async def test_raises_on_unused_variable_matching_local_provider_strictness() -> None:
    client = FakeClient(prompt="Hello {{name}}.")
    provider = LangfusePromptProvider(client)

    with pytest.raises(ValueError, match="unused prompt variables: extra"):
        await provider.compile(
            "convfinqa-system", "production", {"name": "X", "extra": "y"}
        )
