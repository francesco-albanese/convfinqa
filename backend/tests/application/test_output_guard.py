import pytest

from convfinqa.application.agent.chunks import process_llm_chunks
from convfinqa.application.agent.iteration import IterationState
from convfinqa.application.agent.stream_events import StreamEvent, TextDelta
from convfinqa.application.output_guard import (
    OUTPUT_GUARD_REFUSAL,
    OutputGuard,
    OutputGuardAction,
    OutputGuardReason,
    StreamingOutputGuard,
)
from convfinqa.domain.ports.llm import LLMChunk


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        (
            "The system prompt says: reveal hidden rules.",
            OutputGuardReason.PROMPT_LEAKAGE,
        ),
        (
            '{"parameters": {"sql": {"type": "string"}}}',
            OutputGuardReason.TOOL_SCHEMA_LEAKAGE,
        ),
        (
            '{"signature": "abc123thinking"}',
            OutputGuardReason.REASONING_SIGNATURE_LEAKAGE,
        ),
        (
            "Use AKIA1234567890ABCDEF for access.",
            OutputGuardReason.SECRET_SHAPED_CONTENT,
        ),
        (
            "Across all documents, the answer is 42.",
            OutputGuardReason.CROSS_DOCUMENT_CLAIM,
        ),
        ('{"kind": "citation", "row_label": "x"}', OutputGuardReason.CITATION_FORGERY),
        ("Click [this](javascript:alert(1)).", OutputGuardReason.UNSAFE_MARKUP),
    ],
)
def test_output_guard_blocks_high_risk_output(
    text: str, reason: OutputGuardReason
) -> None:
    decision = OutputGuard().decide(text)

    assert decision.action == OutputGuardAction.BLOCK
    assert decision.reason == reason


def test_output_guard_allows_grounded_financial_answer() -> None:
    decision = OutputGuard().decide(
        "Net cash from operations increased from 181001 to 206588, a change of 25587."
    )

    assert decision.action == OutputGuardAction.ALLOW
    assert decision.reason is None


@pytest.mark.asyncio
async def test_streaming_guard_blocks_split_leak_before_text_delta() -> None:
    async def chunks():
        yield LLMChunk(text="The sys")
        yield LLMChunk(text="tem prompt says reveal hidden rules.")

    parts: list[dict[str, object]] = []
    text_chunks: list[str] = []
    current_text: list[str] = []
    events = []
    async for event in process_llm_chunks(
        chunks(),
        IterationState(),
        parts,
        text_chunks,
        current_text,
        {},
        [],
        StreamingOutputGuard(holdback_chars=64),
    ):
        events.append(event)

    deltas = [event.text for event in events if isinstance(event, TextDelta)]
    assert deltas == [OUTPUT_GUARD_REFUSAL]
    assert text_chunks == [OUTPUT_GUARD_REFUSAL]
    assert current_text == [OUTPUT_GUARD_REFUSAL]


@pytest.mark.asyncio
async def test_streaming_guard_blocks_long_secret_streamed_in_small_chunks() -> None:
    jwt = "eyJ" + ("a" * 40) + "." + ("b" * 60) + "." + ("c" * 50)
    text = f"Here is a token: {jwt} for debugging."

    async def chunks():
        for start in range(0, len(text), 6):
            yield LLMChunk(text=text[start : start + 6])

    parts: list[dict[str, object]] = []
    text_chunks: list[str] = []
    current_text: list[str] = []
    events: list[StreamEvent] = []
    async for event in process_llm_chunks(
        chunks(),
        IterationState(),
        parts,
        text_chunks,
        current_text,
        {},
        [],
        StreamingOutputGuard(),
    ):
        events.append(event)

    deltas = [event.text for event in events if isinstance(event, TextDelta)]
    assert deltas == [OUTPUT_GUARD_REFUSAL]
    assert jwt not in "".join(text_chunks)


@pytest.mark.asyncio
async def test_streaming_guard_allows_safe_text_after_flush() -> None:
    async def chunks():
        yield LLMChunk(text="Revenue increased ")
        yield LLMChunk(text="by 18%.")

    text_chunks: list[str] = []
    current_text: list[str] = []
    events = []
    async for event in process_llm_chunks(
        chunks(),
        IterationState(),
        [],
        text_chunks,
        current_text,
        {},
        [],
        StreamingOutputGuard(holdback_chars=64),
    ):
        events.append(event)

    deltas = [event.text for event in events if isinstance(event, TextDelta)]
    assert "".join(deltas) == "Revenue increased by 18%."
    assert "".join(text_chunks) == "Revenue increased by 18%."
