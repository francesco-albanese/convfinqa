from datetime import UTC, datetime

import pytest

from convfinqa.application.agent.stream_events import ConversationResolved, TextDelta
from convfinqa.application.use_cases.send_message_support import (
    DocumentIdRequiredError,
    DocumentNotFoundError,
)
from convfinqa.domain.entities import Conversation, Document
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
async def test_new_conversation_requires_document_id() -> None:
    use_case = build_use_case(FakeConvRepo(), FakeDocRepo(), FakeLLM())

    events = use_case.stream(
        user_id=USER_ID, conversation_id=None, user_text="hi", document_id=None
    )
    with pytest.raises(DocumentIdRequiredError):
        async for _ in events:
            pass


@pytest.mark.asyncio
async def test_existing_conversation_ignores_body_document_id_and_uses_stored_one() -> (
    None
):
    convs = FakeConvRepo()
    stored = Document(
        id="stored-doc",
        ticker="STORED",
        year=2020,
        page=1,
        title="stored title",
        pre_text="stored-pre-marker",
        post_text="stored-post-marker",
        table_data={"k": 1},
    )
    docs = FakeDocRepo(by_id={"stored-doc": stored})
    llm = FakeLLM()

    convs.conversations["conv_existing"] = Conversation(
        id="conv_existing",
        user_id=USER_ID_STR,
        document_id="stored-doc",
        created_at=datetime.now(UTC),
    )
    use_case = build_use_case(convs, docs, llm)

    async for _ in use_case.stream(
        user_id=USER_ID,
        conversation_id="conv_existing",
        user_text="What does the stored document say?",
        document_id="ignored-doc",
    ):
        pass

    assert convs.create_calls == []
    assert "stored-pre-marker" in llm.seen_systems[0]
    assert "STORED" in llm.seen_systems[0]


@pytest.mark.asyncio
async def test_new_conversation_with_unknown_document_id_raises_document_not_found() -> (
    None
):
    use_case = build_use_case(FakeConvRepo(), FakeDocRepo(), FakeLLM())

    events = use_case.stream(
        user_id=USER_ID,
        conversation_id=None,
        user_text="hi",
        document_id="does-not-exist",
    )
    with pytest.raises(DocumentNotFoundError):
        async for _ in events:
            pass


@pytest.mark.asyncio
async def test_new_conversation_emits_resolved_event_and_persists_document_id() -> None:
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    llm = FakeLLM(deltas=("part1", "part2"))
    use_case = build_use_case(convs, docs, llm)

    seen_text: list[str] = []
    seen_resolved: list[str] = []
    async for event in use_case.stream(
        user_id=USER_ID,
        conversation_id=None,
        user_text="How did revenue change in the pinned document?",
        document_id="doc-1",
    ):
        if isinstance(event, TextDelta):
            seen_text.append(event.text)
        if isinstance(event, ConversationResolved):
            seen_resolved.append(event.conversation_id)

    assert seen_resolved == ["conv_created"]
    assert "".join(seen_text) == "part1part2"
    assert convs.create_calls == [(USER_ID, "doc-1")]
    user_msgs = [
        message
        for message in convs.messages_by_conv["conv_created"]
        if message.role == Role.USER
    ]
    assert [message.content for message in user_msgs] == [
        "How did revenue change in the pinned document?"
    ]
