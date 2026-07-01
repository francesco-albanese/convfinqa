import uuid
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

ALICE_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MALLORY_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@dataclass(slots=True)
class _FakeConvRepo(ConversationRepository):
    by_owner: dict[tuple[str, uuid.UUID], tuple[Message, ...]] = field(
        default_factory=dict[tuple[str, uuid.UUID], tuple[Message, ...]]
    )

    async def get(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> Conversation | None:
        del conversation_id, user_id
        return None

    async def create(self, user_id: uuid.UUID, document_id: str) -> Conversation:
        del user_id, document_id
        return Conversation(
            id="x", user_id="x", document_id="x", created_at=datetime.now(UTC)
        )

    async def append_message(self, conversation_id: str, message: Message) -> None:
        del conversation_id, message

    async def list_for_user(
        self, user_id: uuid.UUID
    ) -> tuple[ConversationSummary, ...]:
        del user_id
        return ()

    async def get_messages(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> tuple[Message, ...] | None:
        return self.by_owner.get((conversation_id, user_id))

    async def set_title(self, conversation_id: str, title: str) -> None:
        del conversation_id, title

    async def delete(self, conversation_id: str, user_id: uuid.UUID) -> bool:
        del conversation_id, user_id
        return False


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
    repo = _FakeConvRepo(by_owner={("conv-1", ALICE_UUID): messages})
    use_case = GetChatMessagesUseCase(conversations=repo)

    got = await use_case.execute("conv-1", ALICE_UUID)

    assert got == messages


@pytest.mark.asyncio
async def test_raises_not_found_when_repo_returns_none_for_cross_user_or_unknown() -> (
    None
):
    repo = _FakeConvRepo(by_owner={("conv-1", ALICE_UUID): ()})
    use_case = GetChatMessagesUseCase(conversations=repo)

    with pytest.raises(ConversationNotFoundError):
        await use_case.execute("conv-1", MALLORY_UUID)


@pytest.mark.asyncio
async def test_empty_message_history_returns_empty_tuple_not_not_found() -> None:
    repo = _FakeConvRepo(by_owner={("conv-1", ALICE_UUID): ()})
    use_case = GetChatMessagesUseCase(conversations=repo)

    got = await use_case.execute("conv-1", ALICE_UUID)

    assert got == ()
