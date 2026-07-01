from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CompiledPrompt:
    text: str
    version: int | None = None


class PromptProviderPort(Protocol):
    async def compile(
        self, name: str, label: str, variables: Mapping[str, object]
    ) -> CompiledPrompt: ...


class PromptPublisherPort(Protocol):
    async def latest_content_hash(self, name: str) -> str | None: ...

    async def publish(
        self, name: str, template: str, content_hash: str, labels: Sequence[str]
    ) -> int: ...
