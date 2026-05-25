from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from convfinqa.domain.value_objects import Usage


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMChunk:
    text: str = ""
    reasoning_text: str = ""
    reasoning_event: Literal["start", "delta", "end"] | None = None
    usage: Usage | None = None


class LLMPort(Protocol):
    def stream(
        self,
        messages: Sequence[LLMMessage],
        system: str,
    ) -> AsyncIterator[LLMChunk]: ...
