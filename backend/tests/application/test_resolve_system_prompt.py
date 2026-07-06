from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from convfinqa.application.use_cases.send_message_support import resolve_system_prompt
from convfinqa.domain.ports.prompts import CompiledPrompt


@dataclass
class FakeProvider:
    text_by_label: dict[str, str]
    version_by_label: dict[str, int] = field(default_factory=dict[str, int])
    config: dict[str, Any] = field(default_factory=dict[str, Any])
    calls: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])

    async def compile(
        self, name: str, label: str, variables: Mapping[str, object]
    ) -> CompiledPrompt:
        del variables
        self.calls.append((name, label))
        return CompiledPrompt(
            text=self.text_by_label[label],
            version=self.version_by_label.get(label),
            config=self.config if label == "production" else {},
        )


USER_A = UUID("11111111-1111-1111-1111-111111111111")


async def test_pinned_label_bypasses_ab_entirely() -> None:
    provider = FakeProvider(text_by_label={"latest": "latest text"})

    text, prompt_ref = await resolve_system_prompt(provider, "latest", uuid4(), {})

    assert text == "latest text"
    assert provider.calls == [("convfinqa-system", "latest")]
    assert prompt_ref is None


async def test_disabled_ab_serves_production_with_a_single_fetch() -> None:
    provider = FakeProvider(
        text_by_label={"production": "prod text"},
        version_by_label={"production": 1},
        config={"ab": {"enabled": False}},
    )

    text, prompt_ref = await resolve_system_prompt(provider, "production", uuid4(), {})

    assert text == "prod text"
    assert provider.calls == [("convfinqa-system", "production")]
    assert prompt_ref is not None
    assert prompt_ref.label == "production"
    assert prompt_ref.version == 1


async def test_enabled_ab_routes_to_a_variant_and_links_its_version() -> None:
    provider = FakeProvider(
        text_by_label={"production": "prod text", "git-abc123": "variant text"},
        version_by_label={"production": 1, "git-abc123": 7},
        config={
            "ab": {
                "enabled": True,
                "variants": [{"label": "git-abc123", "weight": 100}],
            }
        },
    )

    text, prompt_ref = await resolve_system_prompt(provider, "production", USER_A, {})

    assert text == "variant text"
    assert provider.calls == [
        ("convfinqa-system", "production"),
        ("convfinqa-system", "git-abc123"),
    ]
    assert prompt_ref is not None
    assert prompt_ref.label == "git-abc123"
    assert prompt_ref.version == 7


async def test_same_user_id_is_routed_to_the_same_variant_across_calls() -> None:
    provider = FakeProvider(
        text_by_label={"production": "prod text", "git-abc123": "variant text"},
        version_by_label={"production": 1, "git-abc123": 7},
        config={
            "ab": {
                "enabled": True,
                "variants": [
                    {"label": "production", "weight": 50},
                    {"label": "git-abc123", "weight": 50},
                ],
            }
        },
    )

    first_text, first_ref = await resolve_system_prompt(
        provider, "production", USER_A, {}
    )
    second_text, second_ref = await resolve_system_prompt(
        provider, "production", USER_A, {}
    )

    assert first_text == second_text
    assert first_ref == second_ref


async def test_malformed_ab_config_degrades_to_production() -> None:
    provider = FakeProvider(
        text_by_label={"production": "prod text"},
        version_by_label={"production": 1},
        config={"ab": {"enabled": True}},
    )

    text, prompt_ref = await resolve_system_prompt(provider, "production", uuid4(), {})

    assert text == "prod text"
    assert provider.calls == [("convfinqa-system", "production")]
    assert prompt_ref is not None
    assert prompt_ref.label == "production"
