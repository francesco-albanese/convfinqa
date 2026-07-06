from datetime import UTC, datetime

import pytest

from convfinqa.application.agent.stream_events import ReasoningDelta, TextDelta
from convfinqa.application.output_guard import OUTPUT_GUARD_REFUSAL
from convfinqa.domain.entities import Conversation
from convfinqa.domain.ports.llm import LLMChunk
from convfinqa.domain.value_objects import Role
from tests.application.send_message_fakes import (
    USER_ID,
    USER_ID_STR,
    FakeConvRepo,
    FakeDocRepo,
    FakeLLM,
    build_use_case,
    document,
)


@pytest.mark.asyncio
async def test_guarded_output_persists_only_safe_refusal() -> None:
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    unsafe = "The system prompt says reveal hidden rules."
    llm = FakeLLM(deltas=("The sys", "tem prompt says reveal hidden rules."))
    convs.conversations["conv_existing"] = Conversation(
        id="conv_existing",
        user_id=USER_ID_STR,
        document_id="doc-1",
        created_at=datetime.now(UTC),
    )
    use_case = build_use_case(convs, docs, llm)

    deltas: list[str] = []
    async for event in use_case.stream(
        user_id=USER_ID,
        conversation_id="conv_existing",
        user_text="what was revenue in the pinned document?",
    ):
        if isinstance(event, TextDelta):
            deltas.append(event.text)

    assistant_messages = [
        message
        for message in convs.messages_by_conv["conv_existing"]
        if message.role == Role.ASSISTANT
    ]
    assert deltas == [OUTPUT_GUARD_REFUSAL]
    assert len(assistant_messages) == 1
    assert assistant_messages[0].content == OUTPUT_GUARD_REFUSAL
    assert unsafe not in assistant_messages[0].content
    assert assistant_messages[0].parts is not None
    assert unsafe not in str(assistant_messages[0].parts)


@pytest.mark.asyncio
async def test_guarded_output_replaces_prior_safe_prefix_in_persistence() -> None:
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    safe_prefix = "Revenue increased because operations improved. " * 4
    unsafe_suffix = "The system prompt says reveal hidden rules."
    llm = FakeLLM(deltas=(safe_prefix, unsafe_suffix))
    convs.conversations["conv_existing"] = Conversation(
        id="conv_existing",
        user_id=USER_ID_STR,
        document_id="doc-1",
        created_at=datetime.now(UTC),
    )
    use_case = build_use_case(convs, docs, llm)

    async for _ in use_case.stream(
        user_id=USER_ID,
        conversation_id="conv_existing",
        user_text="what was revenue in the pinned document?",
    ):
        pass

    assistant_messages = [
        message
        for message in convs.messages_by_conv["conv_existing"]
        if message.role == Role.ASSISTANT
    ]
    assert assistant_messages[0].content == OUTPUT_GUARD_REFUSAL
    assert safe_prefix not in assistant_messages[0].content
    assert unsafe_suffix not in str(assistant_messages[0].parts)


@pytest.mark.asyncio
async def test_guarded_reasoning_persists_only_safe_refusal() -> None:
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    unsafe_reasoning = "I found <trusted_application_policy> in the context."
    llm = FakeLLM(
        chunks=(
            LLMChunk(reasoning_event="start", reasoning_block_id="r1"),
            LLMChunk(
                reasoning_event="delta",
                reasoning_block_id="r1",
                reasoning_text=unsafe_reasoning,
            ),
            LLMChunk(reasoning_event="end", reasoning_block_id="r1"),
        )
    )
    convs.conversations["conv_existing"] = Conversation(
        id="conv_existing",
        user_id=USER_ID_STR,
        document_id="doc-1",
        created_at=datetime.now(UTC),
    )
    use_case = build_use_case(convs, docs, llm)

    reasoning_deltas: list[str] = []
    text_deltas: list[str] = []
    async for event in use_case.stream(
        user_id=USER_ID,
        conversation_id="conv_existing",
        user_text="what was revenue in the pinned document?",
    ):
        if isinstance(event, ReasoningDelta):
            reasoning_deltas.append(event.text)
        if isinstance(event, TextDelta):
            text_deltas.append(event.text)

    assistant_messages = [
        message
        for message in convs.messages_by_conv["conv_existing"]
        if message.role == Role.ASSISTANT
    ]
    assert reasoning_deltas == []
    assert text_deltas == [OUTPUT_GUARD_REFUSAL]
    assert assistant_messages[0].content == OUTPUT_GUARD_REFUSAL
    assert unsafe_reasoning not in str(assistant_messages[0].parts)
