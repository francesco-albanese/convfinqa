from dataclasses import dataclass, field
from datetime import datetime

from src.convfinqa.domain.value_objects import Role, StopReason


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
    created_at: datetime
    messages: tuple[Message, ...] = field(default_factory=tuple)
