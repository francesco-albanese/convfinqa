from convfinqa.domain.entities import ConversationSummary
from convfinqa.domain.ports.repository import ConversationRepository


class ListChatsUseCase:
    def __init__(self, conversations: ConversationRepository) -> None:
        self._conversations = conversations

    async def execute(self, user_id: str) -> tuple[ConversationSummary, ...]:
        return await self._conversations.list_for_user(user_id)
