from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.adapters.prompts.local_file import LocalFilePromptProvider
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.domain.ports.llm import LLMChunk


class StubLLM:
    def __init__(self, responses: list[list[LLMChunk]]) -> None:
        self._responses = list(responses)
        self._call_count = 0
        self.received_wire_messages: list[list[dict[str, Any]]] = []

    @property
    def call_count(self) -> int:
        return self._call_count

    async def stream(
        self,
        messages: Any,
        system: str,
        tools: Any = None,
        generation_name: str | None = None,
        trace_user_id: str | None = None,
        session_id: str | None = None,
        environment: str | None = None,
        model: str | None = None,
        prompt_ref: Any = None,
    ) -> AsyncIterator[LLMChunk]:
        del model
        self.received_wire_messages.append(list(messages))
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        for chunk in self._responses[idx]:
            yield chunk


@dataclass
class FakeConversation:
    id: str = "conv-1"
    user_id: str = "user-1"
    document_id: str = "doc-1"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    title: str | None = "Existing title"
    messages: tuple[Any, ...] = field(default_factory=tuple)


@dataclass
class FakeDocument:
    id: str = "doc-1"
    ticker: str | None = "JKHY"
    year: int | None = 2009
    page: int | None = None
    title: str | None = "Test Doc"
    pre_text: str | None = ""
    post_text: str | None = ""
    table_data: Any = None
    column_order: Any = None


class FakeConversationRepo:
    def __init__(self) -> None:
        self.conv = FakeConversation()
        self.appended: list[Any] = []

    async def get(self, conversation_id: str, user_id: Any) -> FakeConversation:
        return self.conv

    async def create(self, user_id: Any, document_id: str) -> FakeConversation:
        return self.conv

    async def append_message(self, conversation_id: str, message: Any) -> None:
        self.appended.append(message)


class FakeDocumentRepo:
    async def get(self, document_id: str) -> FakeDocument:
        return FakeDocument()


class FakeLock:
    def try_acquire(self, conversation_id: str) -> Any:
        return self

    async def __aenter__(self) -> bool:
        return True

    async def __aexit__(self, *_: Any) -> None:
        pass


class RecordedSpan:
    def __init__(self, call: dict[str, Any]) -> None:
        self._call = call

    def set_output(self, output: str) -> None:
        self._call["output"] = output

    def set_error(self) -> None:
        self._call["level"] = "error"


class RecordingObservability:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    @asynccontextmanager
    async def start_as_current_observation(
        self,
        as_type: str,
        name: str,
        input_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[RecordedSpan]:
        if "input" in kwargs:
            input_data = kwargs.pop("input")
        if kwargs:
            raise TypeError(f"unexpected observation kwargs: {sorted(kwargs)}")
        call = {"as_type": as_type, "name": name, "input": input_data}
        self.calls.append(call)
        yield RecordedSpan(call)

    def propagate_attributes(
        self,
        user_id: str,
        session_id: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> None:
        pass

    def update_current_generation(self, **kwargs: Any) -> None:
        pass

    async def flush(self) -> None:
        pass


def make_use_case(llm: Any) -> SendMessageUseCase:
    return SendMessageUseCase(
        llm=llm,
        conversations=FakeConversationRepo(),  # type: ignore[arg-type]
        documents=FakeDocumentRepo(),  # type: ignore[arg-type]
        locks=FakeLock(),  # type: ignore[arg-type]
        prompt_provider=LocalFilePromptProvider(),
        observability=NoOpLangfuseClient(),  # type: ignore[arg-type]
        llm_model="test-model",
        environment="test",
    )
