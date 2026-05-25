import pytest

from convfinqa.adapters.observability.langfuse_client import (
    NoOpLangfuseClient,
    init_langfuse,
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
