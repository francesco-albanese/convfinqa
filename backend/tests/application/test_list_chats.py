import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from convfinqa.application.use_cases.list_chats import ListChatsUseCase
from convfinqa.domain.entities import (
    Conversation,
    ConversationSummary,
    DocumentSummary,
    Message,
)
from convfinqa.domain.ports.repository import ConversationRepository

ALICE_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
BOB_UUID = uuid.UUID("22222222-2222-2222-2222-222222222222")
NOBODY_UUID = uuid.UUID("33333333-3333-3333-3333-333333333333")


@dataclass(slots=True)
class _FakeConvRepo(ConversationRepository):
    by_user: dict[uuid.UUID, tuple[ConversationSummary, ...]] = field(
        default_factory=dict[uuid.UUID, tuple[ConversationSummary, ...]]
    )
    seen_user_ids: list[uuid.UUID] = field(default_factory=list[uuid.UUID])

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
        self.seen_user_ids.append(user_id)
        return self.by_user.get(user_id, ())

    async def get_messages(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> tuple[Message, ...] | None:
        del conversation_id, user_id
        return None

    async def set_title(self, conversation_id: str, title: str) -> None:
        del conversation_id, title

    async def delete(self, conversation_id: str, user_id: uuid.UUID) -> bool:
        del conversation_id, user_id
        return False


def _summary(conv_id: str, ticker: str) -> ConversationSummary:
    return ConversationSummary(
        id=conv_id,
        document=DocumentSummary(
            id=f"doc-{ticker.lower()}",
            ticker=ticker,
            year=2024,
            page=1,
            title=f"{ticker} 2024",
        ),
        last_message_preview="latest user line",
        last_message_at=datetime(2026, 5, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_returns_only_summaries_for_the_requested_user() -> None:
    alice = (_summary("conv-a1", "AAA"), _summary("conv-a2", "BBB"))
    repo = _FakeConvRepo(
        by_user={
            ALICE_UUID: alice,
            BOB_UUID: (_summary("conv-b1", "CCC"),),
        }
    )
    use_case = ListChatsUseCase(conversations=repo)

    got = await use_case.execute(ALICE_UUID)

    assert got == alice
    assert repo.seen_user_ids == [ALICE_UUID]


@pytest.mark.asyncio
async def test_returns_empty_tuple_when_user_has_no_conversations() -> None:
    use_case = ListChatsUseCase(conversations=_FakeConvRepo())

    got = await use_case.execute(NOBODY_UUID)

    assert got == ()
