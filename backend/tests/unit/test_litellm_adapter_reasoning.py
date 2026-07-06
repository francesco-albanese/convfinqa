from dataclasses import dataclass, field

import pytest

from tests.unit.litellm_reasoning_helpers import (
    FakeChoice,
    FakeChunk,
    FakeDelta,
    collect,
    make_adapter,
)


@pytest.mark.asyncio
async def test_reasoning_chunks_emit_start_delta_end_sequence() -> None:
    chunks = [
        FakeChunk(choices=[FakeChoice(FakeDelta(reasoning_content="think"))]),
        FakeChunk(choices=[FakeChoice(FakeDelta(reasoning_content=" more"))]),
        FakeChunk(choices=[FakeChoice(FakeDelta(content="answer"))]),
    ]
    result = await collect(make_adapter(), chunks)

    events = [(c.reasoning_event, c.reasoning_text, c.text) for c in result]
    assert events[0] == ("start", "", "")
    assert events[1] == ("delta", "think", "")
    assert events[2] == ("delta", " more", "")
    assert events[3] == ("end", "", "")
    assert events[4] == (None, "", "answer")


@pytest.mark.asyncio
async def test_text_only_chunks_emit_no_reasoning_events() -> None:
    chunks = [
        FakeChunk(choices=[FakeChoice(FakeDelta(content="hello "))]),
        FakeChunk(choices=[FakeChoice(FakeDelta(content="world"))]),
    ]
    result = await collect(make_adapter(), chunks)

    assert all(c.reasoning_event is None for c in result)
    assert [c.text for c in result if c.text] == ["hello ", "world"]


@pytest.mark.asyncio
async def test_mixed_reasoning_then_text_emits_correct_sequence() -> None:
    chunks = [
        FakeChunk(choices=[FakeChoice(FakeDelta(reasoning_content="ponder"))]),
        FakeChunk(choices=[FakeChoice(FakeDelta(content="result"))]),
    ]
    result = await collect(make_adapter(), chunks)

    event_types = [c.reasoning_event for c in result]
    assert "start" in event_types
    assert "delta" in event_types
    assert "end" in event_types
    assert [c.text for c in result if c.text] == ["result"]


@pytest.mark.asyncio
async def test_reasoning_content_attribute_not_signature() -> None:
    chunks = [
        FakeChunk(
            choices=[FakeChoice(FakeDelta(reasoning_content="pure thinking text"))]
        ),
        FakeChunk(choices=[FakeChoice(FakeDelta(content="done"))]),
    ]
    result = await collect(make_adapter(), chunks)

    delta_chunks = [c for c in result if c.reasoning_event == "delta"]
    assert len(delta_chunks) == 1
    assert delta_chunks[0].reasoning_text == "pure thinking text"


@dataclass
class _FakeDeltaWithSignature:
    content: str | None = None
    reasoning_content: str | None = None
    signature: str = "anth_sig_SENSITIVE_abc123"


@dataclass
class _FakeChoiceWithSig:
    delta: _FakeDeltaWithSignature = field(default_factory=_FakeDeltaWithSignature)
    finish_reason: str | None = None


@pytest.mark.asyncio
async def test_anthropic_signature_field_never_appears_in_emitted_chunks() -> None:
    chunks = [
        FakeChunk(
            choices=[
                _FakeChoiceWithSig(
                    delta=_FakeDeltaWithSignature(reasoning_content="legit thought")
                )
            ]  # type: ignore[list-item]
        ),
        FakeChunk(choices=[FakeChoice(FakeDelta(content="done"))]),
    ]
    result = await collect(make_adapter(), chunks)

    all_text = " ".join(
        c.reasoning_text + c.text for c in result if c.reasoning_text or c.text
    )
    assert "anth_sig" not in all_text
    assert "SENSITIVE" not in all_text
    assert [c.reasoning_text for c in result if c.reasoning_event == "delta"] == [
        "legit thought"
    ]


@pytest.mark.asyncio
async def test_empty_delta_mid_reasoning_does_not_end_block() -> None:
    chunks = [
        FakeChunk(choices=[FakeChoice(FakeDelta(reasoning_content="part 1"))]),
        FakeChunk(choices=[FakeChoice(FakeDelta())]),
        FakeChunk(choices=[FakeChoice(FakeDelta(reasoning_content="part 2"))]),
        FakeChunk(choices=[FakeChoice(FakeDelta(content="answer"))]),
    ]
    result = await collect(make_adapter(), chunks)

    assert len([c for c in result if c.reasoning_event == "start"]) == 1
    assert len([c for c in result if c.reasoning_event == "end"]) == 1
    delta_events = [c for c in result if c.reasoning_event == "delta"]
    assert "".join(c.reasoning_text for c in delta_events) == "part 1part 2"
