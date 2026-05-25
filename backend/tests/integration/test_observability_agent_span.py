import uuid
from typing import cast

import pytest_asyncio
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.observability.langfuse_client import init_langfuse
from convfinqa.adapters.observability.tracer_provider import (
    init_tracer_provider,
    reset_tracer_provider_for_tests,
)
from convfinqa.config import Settings
from convfinqa.container import for_testing
from convfinqa.container.bootstrap import Container
from convfinqa.domain.ports.llm import LLMPort
from tests.conftest import DEFAULT_DOCUMENT_ID, SEEDED_USER_UUID
from tests.fakes.llm import FakeLLMPort


@pytest_asyncio.fixture(loop_scope="session")
async def observability_container(
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[InMemorySpanExporter, Container]:
    exporter = InMemorySpanExporter()
    # langfuse_enabled=True so init_langfuse returns a real LangfuseClient that
    # writes OTel spans; no keys means no LangfuseSpanProcessor is added, only
    # our test exporter captures the spans.
    settings = Settings(langfuse_enabled=True, environment="test")
    reset_tracer_provider_for_tests()
    init_tracer_provider(settings, extra_processors=[SimpleSpanProcessor(exporter)])
    observability = init_langfuse(settings)
    fake_llm = FakeLLMPort()
    container = for_testing(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        llm=cast(LLMPort, fake_llm),
        observability=observability,
    )
    return exporter, container


async def test_send_message_emits_agent_span_with_trace_attributes(
    observability_container: tuple[InMemorySpanExporter, Container],
) -> None:
    exporter, container = observability_container
    exporter.clear()

    user_id = uuid.UUID(SEEDED_USER_UUID)
    async for _ in container.send_message.stream(
        user_id=user_id,
        conversation_id=None,
        user_text="What is the revenue?",
        document_id=DEFAULT_DOCUMENT_ID,
    ):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    attrs = span.attributes or {}
    assert span.name == "send_message"
    assert attrs.get("user.id") == str(user_id)
    assert "session.id" in attrs
    assert attrs.get("langfuse.observation.type") == "agent"
