from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from convfinqa.adapters.llm.litellm_adapter import LiteLLMAdapter
from convfinqa.domain.ports.llm import LLMChunk


@dataclass
class _FakeDelta:
    content: str | None = None
    reasoning_content: str | None = None


@dataclass
class _FakeChoice:
    delta: _FakeDelta = field(default_factory=_FakeDelta)
    finish_reason: str | None = None


@dataclass
class _FakeUsage:
    prompt_tokens: int = 10
    completion_tokens: int = 5


@dataclass
class _FakeChunk:
    choices: list[_FakeChoice] = field(default_factory=list[_FakeChoice])
    usage: _FakeUsage | None = None


def _make_adapter(
    model: str = "openai/gpt-4o", max_output_tokens: int = 1024
) -> LiteLLMAdapter:
    return LiteLLMAdapter(
        model=model,
        request_timeout_seconds=30.0,
        max_output_tokens=max_output_tokens,
    )


async def _collect(adapter: LiteLLMAdapter, chunks: list[_FakeChunk]) -> list[LLMChunk]:
    async def _fake_stream() -> AsyncIterator[_FakeChunk]:
        for chunk in chunks:
            yield chunk

    async def _open_stream_stub(*args: Any, **kwargs: Any) -> AsyncIterator[_FakeChunk]:
        return _fake_stream()

    messages = [{"role": "user", "content": "hello"}]
    with patch(
        "convfinqa.adapters.llm.litellm_adapter._open_stream",
        new=AsyncMock(side_effect=_open_stream_stub),
    ):
        return [c async for c in adapter.stream(messages, "system")]


@pytest.mark.asyncio
async def test_reasoning_chunks_emit_start_delta_end_sequence() -> None:
    chunks = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(reasoning_content="think"))]),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(reasoning_content=" more"))]),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="answer"))]),
    ]
    adapter = _make_adapter()
    result = await _collect(adapter, chunks)

    events = [(c.reasoning_event, c.reasoning_text, c.text) for c in result]
    assert events[0] == ("start", "", "")
    assert events[1] == ("delta", "think", "")
    assert events[2] == ("delta", " more", "")
    assert events[3] == ("end", "", "")
    assert events[4] == (None, "", "answer")


@pytest.mark.asyncio
async def test_text_only_chunks_emit_no_reasoning_events() -> None:
    chunks = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="hello "))]),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="world"))]),
    ]
    adapter = _make_adapter()
    result = await _collect(adapter, chunks)

    assert all(c.reasoning_event is None for c in result)
    assert [c.text for c in result if c.text] == ["hello ", "world"]


@pytest.mark.asyncio
async def test_mixed_reasoning_then_text_emits_correct_sequence() -> None:
    chunks = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(reasoning_content="ponder"))]),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="result"))]),
    ]
    adapter = _make_adapter()
    result = await _collect(adapter, chunks)

    event_types = [c.reasoning_event for c in result]
    assert "start" in event_types
    assert "delta" in event_types
    assert "end" in event_types

    text_chunks = [c for c in result if c.text]
    assert len(text_chunks) == 1
    assert text_chunks[0].text == "result"


@pytest.mark.asyncio
async def test_reasoning_content_attribute_not_signature() -> None:
    chunks = [
        _FakeChunk(
            choices=[_FakeChoice(_FakeDelta(reasoning_content="pure thinking text"))]
        ),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="done"))]),
    ]
    adapter = _make_adapter()
    result = await _collect(adapter, chunks)

    delta_chunks = [c for c in result if c.reasoning_event == "delta"]
    assert len(delta_chunks) == 1
    assert delta_chunks[0].reasoning_text == "pure thinking text"


@dataclass
class _FakeDeltaWithSignature:
    content: str | None = None
    reasoning_content: str | None = None
    signature: str = "anth_sig_SENSITIVE_abc123"


@pytest.mark.asyncio
async def test_anthropic_signature_field_never_appears_in_emitted_chunks() -> None:
    delta_with_sig = _FakeDeltaWithSignature(reasoning_content="legit thought")

    @dataclass
    class _FakeChoiceWithSig:
        delta: _FakeDeltaWithSignature = field(default_factory=_FakeDeltaWithSignature)
        finish_reason: str | None = None

    chunks_with_sig: list[_FakeChunk] = [
        _FakeChunk(choices=[_FakeChoiceWithSig(delta=delta_with_sig)]),  # type: ignore[list-item]
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="done"))]),
    ]
    adapter = _make_adapter()
    result = await _collect(adapter, chunks_with_sig)

    all_text = " ".join(
        c.reasoning_text + c.text for c in result if c.reasoning_text or c.text
    )
    assert "anth_sig" not in all_text
    assert "SENSITIVE" not in all_text

    delta_chunks = [c for c in result if c.reasoning_event == "delta"]
    assert len(delta_chunks) == 1
    assert delta_chunks[0].reasoning_text == "legit thought"


@pytest.mark.asyncio
async def test_usage_chunk_emitted_when_present() -> None:
    chunks = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="hi"))]),
        _FakeChunk(
            choices=[], usage=_FakeUsage(prompt_tokens=20, completion_tokens=10)
        ),
    ]
    adapter = _make_adapter()
    result = await _collect(adapter, chunks)

    usage_chunks = [c for c in result if c.usage is not None]
    assert len(usage_chunks) == 1
    assert usage_chunks[0].usage is not None
    assert usage_chunks[0].usage.input_tokens == 20
    assert usage_chunks[0].usage.output_tokens == 10


@pytest.mark.asyncio
async def test_gemini_model_does_not_pass_thinking_param() -> None:
    chunks: list[_FakeChunk] = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="hi"))]),
    ]
    adapter = _make_adapter(model="gemini/gemini-2.0-flash")

    captured_kwargs: dict[str, Any] = {}

    async def _fake_stream() -> AsyncIterator[_FakeChunk]:
        for chunk in chunks:
            yield chunk

    async def _open_stream_stub(*args: Any, **kwargs: Any) -> AsyncIterator[_FakeChunk]:
        captured_kwargs.update(kwargs)
        return _fake_stream()

    messages = [{"role": "user", "content": "hello"}]
    with patch(
        "convfinqa.adapters.llm.litellm_adapter._open_stream",
        new=AsyncMock(side_effect=_open_stream_stub),
    ):
        collected: list[LLMChunk] = [
            c async for c in adapter.stream(messages, "system")
        ]

    assert len(collected) > 0
    assert captured_kwargs.get("thinking") is None


@pytest.mark.asyncio
async def test_anthropic_model_omits_thinking_when_max_tokens_cannot_fit_budget() -> None:
    chunks: list[_FakeChunk] = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="hi"))]),
    ]
    adapter = _make_adapter(model="bedrock/anthropic.claude-haiku-4-5")

    captured_kwargs: dict[str, Any] = {}

    async def _fake_stream() -> AsyncIterator[_FakeChunk]:
        for chunk in chunks:
            yield chunk

    async def _open_stream_stub(*args: Any, **kwargs: Any) -> AsyncIterator[_FakeChunk]:
        captured_kwargs.update(kwargs)
        return _fake_stream()

    messages = [{"role": "user", "content": "hello"}]
    with patch(
        "convfinqa.adapters.llm.litellm_adapter._open_stream",
        new=AsyncMock(side_effect=_open_stream_stub),
    ):
        [c async for c in adapter.stream(messages, "system")]

    assert captured_kwargs.get("thinking") is None


@pytest.mark.asyncio
async def test_anthropic_model_caps_thinking_budget_below_max_tokens() -> None:
    chunks: list[_FakeChunk] = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="hi"))]),
    ]
    adapter = _make_adapter(
        model="bedrock/anthropic.claude-haiku-4-5",
        max_output_tokens=2048,
    )

    captured_kwargs: dict[str, Any] = {}

    async def _fake_stream() -> AsyncIterator[_FakeChunk]:
        for chunk in chunks:
            yield chunk

    async def _open_stream_stub(*args: Any, **kwargs: Any) -> AsyncIterator[_FakeChunk]:
        captured_kwargs.update(kwargs)
        return _fake_stream()

    messages = [{"role": "user", "content": "hello"}]
    with patch(
        "convfinqa.adapters.llm.litellm_adapter._open_stream",
        new=AsyncMock(side_effect=_open_stream_stub),
    ):
        [c async for c in adapter.stream(messages, "system")]

    assert captured_kwargs.get("thinking") == {
        "type": "enabled",
        "budget_tokens": 2047,
    }


@pytest.mark.asyncio
async def test_empty_delta_mid_reasoning_does_not_end_block() -> None:
    chunks = [
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(reasoning_content="part 1"))]),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta())]),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(reasoning_content="part 2"))]),
        _FakeChunk(choices=[_FakeChoice(_FakeDelta(content="answer"))]),
    ]
    adapter = _make_adapter()
    result = await _collect(adapter, chunks)

    end_events = [c for c in result if c.reasoning_event == "end"]
    start_events = [c for c in result if c.reasoning_event == "start"]
    delta_events = [c for c in result if c.reasoning_event == "delta"]
    assert len(start_events) == 1
    assert len(end_events) == 1
    assert len(delta_events) == 2
    assert "".join(c.reasoning_text for c in delta_events) == "part 1part 2"
