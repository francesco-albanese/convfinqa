from dataclasses import dataclass, field
from typing import Any

from langfuse.api.commons.errors.not_found_error import NotFoundError

from convfinqa.adapters.prompts.langfuse_publisher import LangfusePromptPublisher


@dataclass
class FakePrompt:
    version: int
    config: dict[str, Any]


@dataclass
class FakeClient:
    existing: dict[str, FakePrompt] = field(default_factory=dict[str, FakePrompt])
    created: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])

    def get_prompt(
        self, name: str, *, label: str, type: str, cache_ttl_seconds: int
    ) -> FakePrompt:
        if name not in self.existing:
            raise NotFoundError(body="not found")
        return self.existing[name]

    def create_prompt(
        self,
        *,
        name: str,
        prompt: str,
        labels: list[str],
        config: dict[str, Any],
        type: str,
    ) -> FakePrompt:
        version = len(self.created) + 1
        self.created.append(
            {"name": name, "prompt": prompt, "labels": labels, "config": config}
        )
        return FakePrompt(version=version, config=config)


async def test_latest_config_returns_none_when_prompt_not_found() -> None:
    client = FakeClient()
    publisher = LangfusePromptPublisher(client)

    result = await publisher.latest_config("convfinqa-system")

    assert result is None


async def test_latest_config_reads_stored_config() -> None:
    client = FakeClient(
        existing={
            "convfinqa-system": FakePrompt(
                version=3, config={"content_hash": "abc", "ab": {"enabled": True}}
            )
        }
    )
    publisher = LangfusePromptPublisher(client)

    result = await publisher.latest_config("convfinqa-system")

    assert result == {"content_hash": "abc", "ab": {"enabled": True}}


async def test_publish_creates_prompt_with_hash_ab_and_labels() -> None:
    client = FakeClient()
    publisher = LangfusePromptPublisher(client)

    version = await publisher.publish(
        "convfinqa-system",
        "Hello {{name}}",
        "hash123",
        ab_config={"enabled": False},
        labels=["latest", "git-abc1234"],
    )

    assert version == 1
    assert client.created[0]["labels"] == ["latest", "git-abc1234"]
    assert client.created[0]["config"] == {
        "content_hash": "hash123",
        "ab": {"enabled": False},
    }
