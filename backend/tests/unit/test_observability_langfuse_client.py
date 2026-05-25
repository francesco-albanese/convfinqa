import pytest
from langfuse._client.attributes import (  # type: ignore[import-untyped]
    LangfuseOtelSpanAttributes,
)
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from convfinqa.adapters.observability.langfuse_client import (
    NoOpLangfuseClient,
    init_langfuse,
)
from convfinqa.adapters.observability.mask import REDACTED
from convfinqa.adapters.observability.tracer_provider import (
    init_tracer_provider,
    reset_tracer_provider_for_tests,
)
from convfinqa.config import Settings


@pytest.fixture
def noop_client() -> NoOpLangfuseClient:
    return NoOpLangfuseClient()


async def test_noop_start_observation_yields_span(
    noop_client: NoOpLangfuseClient,
) -> None:
    async with noop_client.start_as_current_observation(
        as_type="agent",
        name="test_span",
        input={"question": "revenue?"},
    ) as span:
        span.set_output("100")
        span.set_error()


async def test_noop_propagate_attributes_does_not_raise(
    noop_client: NoOpLangfuseClient,
) -> None:
    noop_client.propagate_attributes(
        user_id="user-123",
        session_id="session-abc",
        metadata={"doc": "acme.pdf"},
        tags=["environment:test"],
    )


async def test_noop_flush_does_not_raise(noop_client: NoOpLangfuseClient) -> None:
    await noop_client.flush()


def test_init_langfuse_returns_noop_when_disabled() -> None:
    settings = Settings(langfuse_enabled=False)
    client = init_langfuse(settings)
    assert isinstance(client, NoOpLangfuseClient)


async def test_langfuse_client_redacts_observation_payloads() -> None:
    exporter = InMemorySpanExporter()
    reset_tracer_provider_for_tests()
    try:
        init_tracer_provider(
            Settings(langfuse_enabled=True, environment="test"),
            extra_processors=[SimpleSpanProcessor(exporter)],
        )
        client = init_langfuse(Settings(langfuse_enabled=True, environment="test"))

        async with client.start_as_current_observation(
            as_type="tool",
            name="sql_query",
            input={"user_text": "What is revenue?", "api_key": "sk-secret"},
        ) as span:
            span.set_output('{"token": "secret-token", "rows": 3}')

        [finished_span] = exporter.get_finished_spans()
        attrs = finished_span.attributes or {}
        assert attrs[LangfuseOtelSpanAttributes.OBSERVATION_INPUT] == (
            f'{{"user_text": "{REDACTED}", "api_key": "{REDACTED}"}}'
        )
        assert attrs[LangfuseOtelSpanAttributes.OBSERVATION_OUTPUT] == (
            f'{{"token": "{REDACTED}", "rows": 3}}'
        )
    finally:
        reset_tracer_provider_for_tests()
