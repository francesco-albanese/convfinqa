from typing import Protocol

from convfinqa.domain.entities import Conversation, Message


class ConversationRepository(Protocol):
    async def get(self, conversation_id: str, user_id: str) -> Conversation | None: ...

    async def create(self, user_id: str) -> Conversation: ...

    async def append_message(self, conversation_id: str, message: Message) -> None: ...
