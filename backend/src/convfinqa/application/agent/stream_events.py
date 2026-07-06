from dataclasses import dataclass
from datetime import datetime

from convfinqa.domain.value_objects import StopReason, Usage


@dataclass(frozen=True, slots=True)
class ConversationResolved:
    conversation_id: str


@dataclass(frozen=True, slots=True)
class MessageStarted:
    message_id: str


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ReasoningStart:
    id: str


@dataclass(frozen=True, slots=True)
class ReasoningDelta:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class ReasoningEnd:
    id: str


@dataclass(frozen=True, slots=True)
class ToolCallStart:
    call_id: str
    name: str


@dataclass(frozen=True, slots=True)
class ToolCallArgsComplete:
    call_id: str
    args: str


@dataclass(frozen=True, slots=True)
class ToolResult:
    call_id: str
    result: str
    is_error: bool


@dataclass(frozen=True, slots=True)
class Finish:
    stop_reason: StopReason
    usage: Usage | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    detail: str


@dataclass(frozen=True, slots=True)
class ConcurrentRequest:
    conversation_id: str


@dataclass(frozen=True, slots=True)
class Citation:
    row_label: str
    col_label: str


@dataclass(frozen=True, slots=True)
class ConversationTitle:
    conversation_id: str
    title: str


StreamEvent = (
    ConversationResolved
    | MessageStarted
    | TextDelta
    | ReasoningStart
    | ReasoningDelta
    | ReasoningEnd
    | ToolCallStart
    | ToolCallArgsComplete
    | ToolResult
    | Finish
    | ErrorEvent
    | ConcurrentRequest
    | Citation
    | ConversationTitle
)
