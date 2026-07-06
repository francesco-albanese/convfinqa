from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Any

import pytest

from convfinqa.application.agent.stream_events import ConversationTitle
from convfinqa.domain.entities import Conversation, Message
from convfinqa.domain.ports.llm import LLMChunk
from convfinqa.domain.value_objects import Role
from tests.application.send_message_fakes import (
    USER_ID,
    USER_ID_STR,
    CountingPromptProvider,
    FakeConvRepo,
    FakeDocRepo,
    FakeLLM,
    build_use_case,
    document,
)


@pytest.mark.asyncio
async def test_existing_empty_conversation_generates_title_once_from_first_question() -> (
    None
):
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    llm = FakeLLM(deltas=("answer",), title_deltas=("Cash ", "flow"))
    convs.conversations["conv_existing"] = Conversation(
        id="conv_existing",
        user_id=USER_ID_STR,
        document_id="doc-1",
        created_at=datetime.now(UTC),
        title=None,
    )
    use_case = build_use_case(convs, docs, llm)

    titles: list[str] = []
    async for event in use_case.stream(
        user_id=USER_ID,
        conversation_id="conv_existing",
        user_text="what was cash flow in the pinned document?",
    ):
        if isinstance(event, ConversationTitle):
            titles.append(event.title)

    assert titles == ["Cash flow"]
    assert convs.conversations["conv_existing"].title == "Cash flow"


@pytest.mark.asyncio
async def test_prompt_provider_compiles_once_across_agent_loop_iterations() -> None:
    class _ToolLoopLLM(FakeLLM):
        async def stream(
            self,
            messages: Sequence[dict[str, Any]],
            system: str,
            tools: Any = None,
            generation_name: str | None = None,
            trace_user_id: str | None = None,
            session_id: str | None = None,
            environment: str | None = None,
            model: str | None = None,
        ) -> AsyncIterator[LLMChunk]:
            self.seen_systems.append(system)
            self.seen_messages.append(list(messages))
            del tools, generation_name, trace_user_id, session_id, environment, model
            yield LLMChunk(
                tool_call_event="start",
                tool_call_id="c1",
                tool_call_name="add",
            )
            yield LLMChunk(
                tool_call_event="delta",
                tool_call_id="c1",
                tool_call_delta='{"a":"1","b":"2"}',
            )
            yield LLMChunk(tool_call_event="complete", tool_call_id="c1")
            yield LLMChunk(finish_reason_tool_use=True)

    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    llm = _ToolLoopLLM()
    provider = CountingPromptProvider()
    convs.conversations["conv_existing"] = Conversation(
        id="conv_existing",
        user_id=USER_ID_STR,
        document_id="doc-1",
        created_at=datetime.now(UTC),
        title="Existing title",
    )
    use_case = build_use_case(convs, docs, llm, prompt_provider=provider)

    async for _ in use_case.stream(
        user_id=USER_ID,
        conversation_id="conv_existing",
        user_text="what was revenue in the pinned document?",
    ):
        pass

    assert len(provider.calls) == 1
    name, label, variables = provider.calls[0]
    assert (name, label) == ("convfinqa-system", "production")
    assert {"title", "ticker", "year", "pre_text", "post_text", "tool_docs"}.issubset(
        variables
    )
    assert len(llm.seen_systems) == 10
    assert set(llm.seen_systems) == {"compiled prompt"}


@pytest.mark.asyncio
async def test_existing_conversation_with_prior_user_message_does_not_regenerate_title() -> (
    None
):
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    llm = FakeLLM(deltas=("answer",), title_deltas=("Replacement",))
    convs.conversations["conv_existing"] = Conversation(
        id="conv_existing",
        user_id=USER_ID_STR,
        document_id="doc-1",
        created_at=datetime.now(UTC),
        messages=(
            Message(
                id="msg-user-1",
                conversation_id="conv_existing",
                role=Role.USER,
                content="first question",
                created_at=datetime.now(UTC),
            ),
        ),
        title=None,
    )
    use_case = build_use_case(convs, docs, llm)

    titles: list[str] = []
    async for event in use_case.stream(
        user_id=USER_ID,
        conversation_id="conv_existing",
        user_text="follow up?",
    ):
        if isinstance(event, ConversationTitle):
            titles.append(event.title)

    assert titles == []
    assert convs.conversations["conv_existing"].title is None
