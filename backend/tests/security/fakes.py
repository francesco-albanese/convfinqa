import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from convfinqa.adapters.observability.langfuse_client import NoOpLangfuseClient
from convfinqa.adapters.prompts.local_file import LocalFilePromptProvider
from convfinqa.application.suspicious_attempt_throttle import SuspiciousAttemptThrottle
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.domain.entities import Document
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.rate_limit import RateLimitPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from tests.application.send_message_fakes import (
    AlwaysAcquireLock,
    FakeConvRepo,
    FakeDocRepo,
)
from tests.application.send_message_fakes import (
    document as _document,
)
from tests.fakes.llm import FakeLLMPort

USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


@dataclass(slots=True)
class FakeRateLimit:
    next_count: int = 1
    calls: list[tuple[str, uuid.UUID, datetime, datetime]] = field(
        default_factory=list[tuple[str, uuid.UUID, datetime, datetime]]
    )

    async def increment(
        self,
        scope: str,
        user_id: uuid.UUID,
        window_start: datetime,
        expires_at: datetime,
    ) -> int:
        self.calls.append((scope, user_id, window_start, expires_at))
        count = self.next_count
        self.next_count += 1
        return count


def document(doc_id: str = "doc-sec") -> Document:
    return _document(doc_id)


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
