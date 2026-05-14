from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from convfinqa.application.use_cases.get_chat_messages import (
    ConversationNotFoundError,
    GetChatMessagesUseCase,
)
from convfinqa.domain.entities import (
    Conversation,
    ConversationSummary,
    Message,
)
from convfinqa.domain.ports.repository import ConversationRepository
from convfinqa.domain.value_objects import Role


@dataclass(slots=True)
class _FakeConvRepo(ConversationRepository):
    by_owner: dict[tuple[str, str], tuple[Message, ...]] = field(
        default_factory=dict[tuple[str, str], tuple[Message, ...]]
    )

    async def get(self, conversation_id: str, user_id: str) -> Conversation | None:
        del conversation_id, user_id
        return None

    async def create(self, user_id: str, document_id: str) -> Conversation:
        del user_id, document_id
        return Conversation(
            id="x", user_id="x", document_id="x", created_at=datetime.now(UTC)
        )

    async def append_message(self, conversation_id: str, message: Message) -> None:
        del conversation_id, message

    async def list_for_user(self, user_id: str) -> tuple[ConversationSummary, ...]:
        del user_id
        return ()

    async def get_messages(
        self, conversation_id: str, user_id: str
    ) -> tuple[Message, ...] | None:
        return self.by_owner.get((conversation_id, user_id))


def _message(msg_id: str, role: Role, content: str) -> Message:
    return Message(
        id=msg_id,
        conversation_id="conv-1",
        role=role,
        content=content,
        created_at=datetime(2026, 5, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_returns_messages_when_conversation_belongs_to_user() -> None:
    messages = (
        _message("m-1", Role.USER, "hi"),
        _message("m-2", Role.ASSISTANT, "hello"),
    )
    repo = _FakeConvRepo(by_owner={("conv-1", "alice"): messages})
    use_case = GetChatMessagesUseCase(conversations=repo)

    got = await use_case.execute("conv-1", "alice")

    assert got == messages


@pytest.mark.asyncio
async def test_raises_not_found_when_repo_returns_none_for_cross_user_or_unknown() -> (
    None
):
    repo = _FakeConvRepo(by_owner={("conv-1", "alice"): ()})
    use_case = GetChatMessagesUseCase(conversations=repo)

    with pytest.raises(ConversationNotFoundError):
        await use_case.execute("conv-1", "mallory")


@pytest.mark.asyncio
async def test_empty_message_history_returns_empty_tuple_not_not_found() -> None:
    repo = _FakeConvRepo(by_owner={("conv-1", "alice"): ()})
    use_case = GetChatMessagesUseCase(conversations=repo)

    got = await use_case.execute("conv-1", "alice")

    assert got == ()
