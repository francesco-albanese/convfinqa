from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CompiledPrompt:
    text: str
    version: int | None = None
    config: Mapping[str, object] = field(default_factory=dict[str, object])


class PromptProviderPort(Protocol):
    async def compile(
        self, name: str, label: str, variables: Mapping[str, object]
    ) -> CompiledPrompt: ...


class PromptPublisherPort(Protocol):
    async def latest_config(self, name: str) -> Mapping[str, object] | None: ...

    async def publish(
        self,
        name: str,
        template: str,
        content_hash: str,
        ab_config: Mapping[str, object],
        labels: Sequence[str],
    ) -> int: ...
