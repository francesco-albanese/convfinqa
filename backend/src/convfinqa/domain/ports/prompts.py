from collections.abc import Mapping
from typing import Protocol


class PromptProviderPort(Protocol):
    def compile(
        self, name: str, label: str, variables: Mapping[str, object]
    ) -> str: ...
