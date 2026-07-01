from dataclasses import dataclass

import pytest

from convfinqa.adapters.prompts.langfuse_provider import LangfusePromptProvider


@dataclass
class FakePrompt:
    prompt: str


@dataclass
class FakeClient:
    prompt: str
    seen_labels: list[str] | None = None

    def get_prompt(
        self, name: str, *, label: str, type: str, cache_ttl_seconds: int
    ) -> FakePrompt:
        if self.seen_labels is not None:
            self.seen_labels.append(label)
        return FakePrompt(prompt=self.prompt)


async def test_fetches_by_label_and_compiles_variables() -> None:
    seen_labels: list[str] = []
    client = FakeClient(prompt="Hello {{name}}.", seen_labels=seen_labels)
    provider = LangfusePromptProvider(client)

    compiled = await provider.compile("convfinqa-system", "production", {"name": "X"})

    assert compiled == "Hello X."
    assert seen_labels == ["production"]


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
