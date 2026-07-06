from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from convfinqa.application.evals.experiment_runner import replay_dialogue
from convfinqa.domain.ports.llm import LLMChunk
from tests.application.send_message_fakes import (
    USER_ID,
    FakeConvRepo,
    FakeDocRepo,
    build_use_case,
    document,
)


@dataclass(slots=True)
class ScriptedTurnLLM:
    answers_by_turn: list[str]
    seen_document_ids: list[str | None] = field(default_factory=list[str | None])
    call_index: int = 0

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
        prompt_ref: Any = None,
    ) -> AsyncIterator[LLMChunk]:
        del (
            messages,
            system,
            tools,
            generation_name,
            trace_user_id,
            session_id,
            environment,
            model,
            prompt_ref,
        )
        answer = self.answers_by_turn[self.call_index]
        self.call_index += 1
        yield LLMChunk(text=answer)


async def test_replay_dialogue_scores_each_turn_and_continues_the_conversation() -> (
    None
):
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    llm = ScriptedTurnLLM(
        answers_by_turn=[
            "The answer is 206588 in the pinned document.",
            "The answer is 999 in the pinned document.",
        ]
    )
    use_case = build_use_case(convs, docs, llm)

    result = await replay_dialogue(
        send_message=use_case,
        user_id=USER_ID,
        document_id="doc-1",
        questions=[
            "what was net cash from operations in the pinned document?",
            "what about the prior year in the pinned document?",
        ],
        gold_answers=["206588", "181001"],
    )

    assert [turn.passed for turn in result.turns] == [True, False]
    assert result.turn_accuracy == 0.5
    assert result.all_turns_correct is False
    assert len(convs.conversations) == 1
    assert len(convs.create_calls) == 1


async def test_replay_dialogue_all_turns_correct() -> None:
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    llm = ScriptedTurnLLM(
        answers_by_turn=["18% in the pinned document."],
    )
    use_case = build_use_case(convs, docs, llm)

    result = await replay_dialogue(
        send_message=use_case,
        user_id=USER_ID,
        document_id="doc-1",
        questions=["what was the percentage change in the pinned document?"],
        gold_answers=["18%"],
    )

    assert result.turn_accuracy == 1.0
    assert result.all_turns_correct is True
