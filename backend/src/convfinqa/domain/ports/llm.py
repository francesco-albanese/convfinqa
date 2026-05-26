from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from convfinqa.domain.value_objects import Usage


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LLMChunk:
    text: str = ""
    reasoning_text: str = ""
    reasoning_event: Literal["start", "delta", "end"] | None = None
    reasoning_block_id: str | None = None
    reasoning_signature: str | None = None
    tool_call_event: Literal["start", "delta", "complete"] | None = None
    tool_call_id: str | None = None
    tool_call_name: str | None = None
    tool_call_delta: str | None = None
    finish_reason_tool_use: bool = False
    usage: Usage | None = None


class LLMPort(Protocol):
    def stream(
        self,
        messages: Sequence[dict[str, Any]],
        system: str,
        tools: Sequence[LLMToolSpec] | None = None,
        generation_name: str | None = None,
        trace_user_id: str | None = None,
        session_id: str | None = None,
        environment: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[LLMChunk]: ...
