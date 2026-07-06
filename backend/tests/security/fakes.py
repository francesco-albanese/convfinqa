import uuid
from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.adapters.prompts.local_file import LocalFilePromptProvider
from convfinqa.application.suspicious_attempt_throttle import SuspiciousAttemptThrottle
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.domain.entities import (
    Conversation,
    ConversationSummary,
    Document,
    Message,
)
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.rate_limit import RateLimitPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from tests.fakes.llm import FakeLLMPort

USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@dataclass(slots=True)
class FakeRateLimit:
    next_count: int = 1
    calls: list[tuple[uuid.UUID, datetime, datetime]] = field(
        default_factory=list[tuple[uuid.UUID, datetime, datetime]]
    )

    async def increment(
        self, user_id: uuid.UUID, window_start: datetime, expires_at: datetime
    ) -> int:
        self.calls.append((user_id, window_start, expires_at))
        count = self.next_count
        self.next_count += 1
        return count


@dataclass(slots=True)
class FakeConvRepo:
    conversations: dict[str, Conversation] = field(
        default_factory=dict[str, Conversation]
    )
    messages_by_conv: dict[str, list[Message]] = field(
        default_factory=dict[str, list[Message]]
    )

    async def get(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> Conversation | None:
        conv = self.conversations.get(conversation_id)
        if conv is None or conv.user_id != str(user_id):
            return None
        return conv

    async def create(self, user_id: uuid.UUID, document_id: str) -> Conversation:
        conv = Conversation(
            id="conv_security",
            user_id=str(user_id),
            document_id=document_id,
            created_at=datetime.now(UTC),
        )
        self.conversations[conv.id] = conv
        return conv

    async def append_message(self, conversation_id: str, message: Message) -> None:
        self.messages_by_conv.setdefault(conversation_id, []).append(message)

    async def set_title(self, conversation_id: str, title: str) -> None:
        del conversation_id, title

    async def list_for_user(
        self, user_id: uuid.UUID
    ) -> tuple[ConversationSummary, ...]:
        del user_id
        return ()

    async def get_messages(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> tuple[Message, ...] | None:
        del conversation_id, user_id
        return None


@dataclass(slots=True)
class FakeDocRepo:
    by_id: dict[str, Document] = field(default_factory=dict[str, Document])

    async def get(self, document_id: str) -> Document | None:
        return self.by_id.get(document_id)


class AlwaysAcquireLock:
    def try_acquire(self, conversation_id: str) -> AbstractAsyncContextManager[bool]:
        del conversation_id
        return self._scope()

    @asynccontextmanager
    async def _scope(self) -> AsyncGenerator[bool]:
        yield True


def document(doc_id: str = "doc-sec") -> Document:
    return Document(
        id=doc_id,
        ticker="SEC",
        year=2024,
        page=1,
        title="security fixture",
        pre_text="pre",
        post_text="post",
        table_data={},
    )


def build_use_case(
    convs: FakeConvRepo,
    docs: FakeDocRepo,
    llm: FakeLLMPort,
    rate_limit: FakeRateLimit | None = None,
    max_attempts: int = 5,
) -> SendMessageUseCase:
    throttle = (
        SuspiciousAttemptThrottle(
            rate_limit=cast(RateLimitPort, rate_limit),
            max_attempts=max_attempts,
            window_seconds=300,
        )
        if rate_limit is not None
        else None
    )
    return SendMessageUseCase(
        llm=cast(LLMPort, llm),
        conversations=cast(ConversationRepository, convs),
        documents=cast(DocumentRepository, docs),
        locks=cast(ConversationLockPort, AlwaysAcquireLock()),
        prompt_provider=LocalFilePromptProvider(),
        observability=NoOpLangfuseClient(),  # type: ignore[arg-type]
        llm_model="test-model",
        environment="test",
        suspicious_throttle=throttle,
    )
