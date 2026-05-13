from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from convfinqa.domain.value_objects import Role, StopReason


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    conversation_id: str
    role: Role
    content: str
    created_at: datetime
    stop_reason: StopReason | None = None


@dataclass(frozen=True, slots=True)
class Conversation:
    id: str
    user_id: str
    document_id: str
    created_at: datetime
    messages: tuple[Message, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    ticker: str | None
    year: int | None
    page: int | None
    title: str | None
    pre_text: str | None
    post_text: str | None
    table_data: dict[str, Any] | None
    column_order: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    id: str
    ticker: str | None
    year: int | None
    page: int | None
    title: str | None


@dataclass(frozen=True, slots=True)
class DocumentListPage:
    items: tuple[DocumentSummary, ...]
    next_cursor: str | None
