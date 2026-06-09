import uuid

from convfinqa.application.use_cases.send_message_support import (
    ConversationNotFoundError,
)
from convfinqa.domain.ports.repository import ConversationRepository

__all__ = ["ConversationNotFoundError", "DeleteConversationUseCase"]


class DeleteConversationUseCase:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def execute(self, conversation_id: str, user_id: uuid.UUID) -> None:
        deleted = await self._conversations.delete(conversation_id, user_id)
        if not deleted:
            raise ConversationNotFoundError(conversation_id)
