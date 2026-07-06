from collections.abc import Mapping, Sequence
from typing import Protocol


class PromptProviderPort(Protocol):
    async def compile(
        self, name: str, label: str, variables: Mapping[str, object]
    ) -> str: ...


class PromptPublisherPort(Protocol):
    async def latest_content_hash(self, name: str) -> str | None: ...

    async def publish(
        self, name: str, template: str, content_hash: str, labels: Sequence[str]
    ) -> int: ...
