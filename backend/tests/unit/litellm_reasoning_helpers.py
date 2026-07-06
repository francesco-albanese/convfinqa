from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

from convfinqa.adapters.llm.litellm_adapter import LiteLLMAdapter
from convfinqa.domain.ports.llm import LLMChunk


@dataclass
class FakeDelta:
    content: str | None = None
    reasoning_content: str | None = None


@dataclass
class FakeChoice:
    delta: FakeDelta = field(default_factory=FakeDelta)
    finish_reason: str | None = None


@dataclass
class FakeUsage:
    prompt_tokens: int = 10
    completion_tokens: int = 5


def _empty_choices() -> list[Any]:
    return []


@dataclass
class FakeChunk:
    choices: list[Any] = field(default_factory=_empty_choices)
    usage: FakeUsage | None = None


def make_adapter(
    model: str = "openai/gpt-4o", max_output_tokens: int = 1024
) -> LiteLLMAdapter:
    return LiteLLMAdapter(
        model=model,
        request_timeout_seconds=30.0,
        max_output_tokens=max_output_tokens,
    )


async def collect(adapter: LiteLLMAdapter, chunks: list[FakeChunk]) -> list[LLMChunk]:
    async def fake_stream() -> AsyncIterator[FakeChunk]:
        for chunk in chunks:
            yield chunk

    async def open_stream_stub(*args: Any, **kwargs: Any) -> AsyncIterator[FakeChunk]:
        return fake_stream()

    messages = [{"role": "user", "content": "hello"}]
    with patch(
        "convfinqa.adapters.llm.litellm_adapter._open_stream",
        new=AsyncMock(side_effect=open_stream_stub),
    ):
        return [c async for c in adapter.stream(messages, "system")]


async def collect_with_kwargs_capture(
    adapter: LiteLLMAdapter, chunks: list[FakeChunk]
) -> tuple[list[LLMChunk], dict[str, Any]]:
    captured_kwargs: dict[str, Any] = {}

    async def fake_stream() -> AsyncIterator[FakeChunk]:
        for chunk in chunks:
            yield chunk

    async def open_stream_stub(*args: Any, **kwargs: Any) -> AsyncIterator[FakeChunk]:
        captured_kwargs.update(kwargs)
        return fake_stream()

    messages = [{"role": "user", "content": "hello"}]
    with patch(
        "convfinqa.adapters.llm.litellm_adapter._open_stream",
        new=AsyncMock(side_effect=open_stream_stub),
    ):
        collected = [c async for c in adapter.stream(messages, "system")]

    return collected, captured_kwargs
