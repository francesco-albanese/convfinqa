from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from src.convfinqa.domain.value_objects import Usage


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMChunk:
    text: str = ""
    usage: Usage | None = None


class LLMPort(Protocol):
    def stream(
        self,
        messages: Sequence[LLMMessage],
        system: str,
    ) -> AsyncIterator[LLMChunk]: ...
