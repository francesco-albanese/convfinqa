import pytest

from tests.unit.litellm_reasoning_helpers import (
    FakeChoice,
    FakeChunk,
    FakeDelta,
    FakeUsage,
    collect,
    collect_with_kwargs_capture,
    make_adapter,
)


@pytest.mark.asyncio
async def test_usage_chunk_emitted_when_present() -> None:
    chunks = [
        FakeChunk(choices=[FakeChoice(FakeDelta(content="hi"))]),
        FakeChunk(choices=[], usage=FakeUsage(prompt_tokens=20, completion_tokens=10)),
    ]
    result = await collect(make_adapter(), chunks)

    usage_chunks = [c for c in result if c.usage is not None]
    assert len(usage_chunks) == 1
    assert usage_chunks[0].usage is not None
    assert usage_chunks[0].usage.input_tokens == 20
    assert usage_chunks[0].usage.output_tokens == 10


@pytest.mark.asyncio
async def test_gemini_model_does_not_pass_thinking_param() -> None:
    chunks = [FakeChunk(choices=[FakeChoice(FakeDelta(content="hi"))])]
    adapter = make_adapter(model="gemini/gemini-2.0-flash")

    collected, captured_kwargs = await collect_with_kwargs_capture(adapter, chunks)

    assert len(collected) > 0
    assert captured_kwargs.get("thinking") is None


@pytest.mark.asyncio
async def test_anthropic_model_omits_thinking_when_max_tokens_cannot_fit_budget() -> (
    None
):
    chunks = [FakeChunk(choices=[FakeChoice(FakeDelta(content="hi"))])]
    adapter = make_adapter(model="bedrock/anthropic.claude-haiku-4-5")

    _, captured_kwargs = await collect_with_kwargs_capture(adapter, chunks)

    assert captured_kwargs.get("thinking") is None


@pytest.mark.asyncio
async def test_anthropic_model_caps_thinking_budget_below_max_tokens() -> None:
    chunks = [FakeChunk(choices=[FakeChoice(FakeDelta(content="hi"))])]
    adapter = make_adapter(
        model="bedrock/anthropic.claude-haiku-4-5",
        max_output_tokens=2048,
    )

    _, captured_kwargs = await collect_with_kwargs_capture(adapter, chunks)

    assert captured_kwargs.get("thinking") == {
        "type": "enabled",
        "budget_tokens": 2047,
    }
