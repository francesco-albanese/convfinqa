import uuid
from typing import Protocol

from convfinqa.domain.entities import (
    Conversation,
    ConversationSummary,
    Document,
    Message,
)


class ConversationRepository(Protocol):
    async def get(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> Conversation | None: ...

    async def create(self, user_id: uuid.UUID, document_id: str) -> Conversation: ...

    async def append_message(self, conversation_id: str, message: Message) -> None: ...

    async def list_for_user(
        self, user_id: uuid.UUID
    ) -> tuple[ConversationSummary, ...]: ...

    async def get_messages(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> tuple[Message, ...] | None: ...

    async def set_title(self, conversation_id: str, title: str) -> None: ...


class DocumentRepository(Protocol):
    async def get(self, document_id: str) -> Document | None: ...
