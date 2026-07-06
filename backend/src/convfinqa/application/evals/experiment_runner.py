from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from convfinqa.application.agent.stream_events import ConversationResolved, TextDelta
from convfinqa.application.evals.answer_matching import score_answer
from convfinqa.application.use_cases.send_message import SendMessageUseCase


@dataclass(frozen=True, slots=True)
class TurnResult:
    question: str
    model_answer: str
    gold_answer: str
    passed: bool


@dataclass(frozen=True, slots=True)
class DialogueResult:
    turns: tuple[TurnResult, ...]

    @property
    def turn_accuracy(self) -> float:
        if not self.turns:
            return 0.0
        return sum(1 for turn in self.turns if turn.passed) / len(self.turns)

    @property
    def all_turns_correct(self) -> bool:
        return bool(self.turns) and all(turn.passed for turn in self.turns)


async def replay_dialogue(
    send_message: SendMessageUseCase,
    user_id: UUID,
    document_id: str,
    questions: Sequence[str],
    gold_answers: Sequence[str],
    model: str | None = None,
) -> DialogueResult:
    conversation_id: str | None = None
    turns: list[TurnResult] = []

    for question, gold in zip(questions, gold_answers, strict=True):
        text_parts: list[str] = []
        async for event in send_message.stream(
            user_id=user_id,
            conversation_id=conversation_id,
            user_text=question,
            document_id=document_id if conversation_id is None else None,
            model=model,
        ):
            if isinstance(event, ConversationResolved):
                conversation_id = event.conversation_id
            elif isinstance(event, TextDelta):
                text_parts.append(event.text)

        model_answer = "".join(text_parts)
        result = score_answer(model_answer, gold)
        turns.append(
            TurnResult(
                question=question,
                model_answer=model_answer,
                gold_answer=gold,
                passed=result.passed,
            )
        )

    return DialogueResult(turns=tuple(turns))
