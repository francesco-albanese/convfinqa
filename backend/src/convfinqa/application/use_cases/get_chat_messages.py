from convfinqa.application.use_cases.send_message import ConversationNotFoundError
from convfinqa.domain.entities import Message
from convfinqa.domain.ports.repository import ConversationRepository

__all__ = ["ConversationNotFoundError", "GetChatMessagesUseCase"]


class GetChatMessagesUseCase:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def execute(self, conversation_id: str, user_id: str) -> tuple[Message, ...]:
        messages = await self._conversations.get_messages(conversation_id, user_id)
        if messages is None:
            raise ConversationNotFoundError(conversation_id)
        return messages
