from collections.abc import AsyncGenerator, AsyncIterator, Mapping, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.adapters.prompts.local_file import LocalFilePromptProvider
from convfinqa.application.prompt_injection_detector import (
    PromptInjectionDecision,
    PromptInjectionDetector,
    PromptInjectionSurface,
)
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.domain.entities import (
    Conversation,
    ConversationSummary,
    Document,
    Message,
)
from convfinqa.domain.ports.llm import LLMChunk, LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.prompts import PromptProviderPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)

USER_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID_STR = str(USER_ID)


@dataclass(slots=True)
class FakeConvRepo:
    conversations: dict[str, Conversation] = field(
        default_factory=dict[str, Conversation]
    )
    create_calls: list[tuple[UUID, str]] = field(default_factory=list[tuple[UUID, str]])
    messages_by_conv: dict[str, list[Message]] = field(
        default_factory=dict[str, list[Message]]
    )

    async def get(self, conversation_id: str, user_id: UUID) -> Conversation | None:
        conv = self.conversations.get(conversation_id)
        if conv is None or conv.user_id != str(user_id):
            return None
        return conv

    async def create(self, user_id: UUID, document_id: str) -> Conversation:
        self.create_calls.append((user_id, document_id))
        conv = Conversation(
            id="conv_created",
            user_id=str(user_id),
            document_id=document_id,
            created_at=datetime.now(UTC),
        )
        self.conversations[conv.id] = conv
        return conv

    async def append_message(self, conversation_id: str, message: Message) -> None:
        self.messages_by_conv.setdefault(conversation_id, []).append(message)

    async def set_title(self, conversation_id: str, title: str) -> None:
        conv = self.conversations[conversation_id]
        if conv.title:
            return
        self.conversations[conversation_id] = Conversation(
            id=conv.id,
            user_id=conv.user_id,
            document_id=conv.document_id,
            created_at=conv.created_at,
            messages=conv.messages,
            title=title,
        )

    async def list_for_user(self, user_id: UUID) -> tuple[ConversationSummary, ...]:
        del user_id
        return ()

    async def get_messages(
        self, conversation_id: str, user_id: UUID
    ) -> tuple[Message, ...] | None:
        del conversation_id, user_id
        return None


@dataclass(slots=True)
class FakeDocRepo:
    by_id: dict[str, Document] = field(default_factory=dict[str, Document])

    async def get(self, document_id: str) -> Document | None:
        return self.by_id.get(document_id)


@dataclass(slots=True)
class AlwaysAcquireLock:
    seen: list[str] = field(default_factory=list[str])

    def try_acquire(self, conversation_id: str) -> AbstractAsyncContextManager[bool]:
        self.seen.append(conversation_id)
        return self._scope()

    @asynccontextmanager
    async def _scope(self) -> AsyncGenerator[bool]:
        yield True


@dataclass(slots=True)
class FakeLLM:
    deltas: tuple[str, ...] = ("ok",)
    chunks: tuple[LLMChunk, ...] | None = None
    title_deltas: tuple[str, ...] = ("Title",)
    seen_systems: list[str] = field(default_factory=list[str])
    seen_messages: list[list[dict[str, Any]]] = field(
        default_factory=list[list[dict[str, Any]]]
    )

    async def stream(
        self,
        messages: Sequence[dict[str, Any]],
        system: str,
        tools: Any = None,
        generation_name: str | None = None,
        trace_user_id: str | None = None,
        session_id: str | None = None,
        environment: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[LLMChunk]:
        if generation_name == "title-generation":
            for d in self.title_deltas:
                yield LLMChunk(text=d)
            return
        self.seen_systems.append(system)
        self.seen_messages.append(list(messages))
        del tools, model
        if self.chunks is not None:
            for chunk in self.chunks:
                yield chunk
            return
        for d in self.deltas:
            yield LLMChunk(text=d)


class FailingPromptInjectionDetector(PromptInjectionDetector):
    def decide(
        self,
        text: str,
        surface: PromptInjectionSurface = PromptInjectionSurface.USER_TEXT,
    ) -> PromptInjectionDecision:
        del text, surface
        raise RuntimeError("detector unavailable")


@dataclass(slots=True)
class CountingPromptProvider:
    calls: list[tuple[str, str, dict[str, object]]] = field(
        default_factory=list[tuple[str, str, dict[str, object]]]
    )

    def compile(self, name: str, label: str, variables: Mapping[str, object]) -> str:
        self.calls.append((name, label, dict(variables)))
        return "compiled prompt"


def document(doc_id: str = "doc-1") -> Document:
    return Document(
        id=doc_id,
        ticker="X",
        year=2024,
        page=1,
        title="t",
        pre_text="pre",
        post_text="post",
        table_data={},
    )


def build_use_case(
    convs: FakeConvRepo,
    docs: FakeDocRepo,
    llm: FakeLLM,
    prompt_injection_detector: PromptInjectionDetector | None = None,
    prompt_provider: PromptProviderPort | None = None,
) -> SendMessageUseCase:
    return SendMessageUseCase(
        llm=cast(LLMPort, llm),
        conversations=cast(ConversationRepository, convs),
        documents=cast(DocumentRepository, docs),
        locks=cast(ConversationLockPort, AlwaysAcquireLock()),
        prompt_provider=prompt_provider or LocalFilePromptProvider(),
        observability=NoOpLangfuseClient(),  # type: ignore[arg-type]
        llm_model="test-model",
        environment="test",
        prompt_injection_detector=prompt_injection_detector,
    )
