from collections.abc import Callable, Coroutine
from typing import Any
from uuid import uuid4

from langfuse import Evaluation

from convfinqa.application.evals.experiment_runner import replay_dialogue
from convfinqa.application.use_cases.send_message import SendMessageUseCase


def build_task(
    send_message: SendMessageUseCase, model: str | None
) -> Callable[..., Coroutine[Any, Any, dict[str, Any]]]:
    async def task(*, item: Any, **kwargs: Any) -> dict[str, Any]:
        del kwargs
        result = await replay_dialogue(
            send_message=send_message,
            user_id=uuid4(),
            document_id=item.input["document_id"],
            questions=item.input["questions"],
            gold_answers=item.expected_output,
            model=model,
        )
        return {
            "turns": [
                {
                    "question": turn.question,
                    "model_answer": turn.model_answer,
                    "gold_answer": turn.gold_answer,
                    "passed": turn.passed,
                }
                for turn in result.turns
            ],
            "turn_accuracy": result.turn_accuracy,
            "all_turns_correct": result.all_turns_correct,
        }

    return task


def turn_accuracy_evaluator(
    *, output: dict[str, Any], **kwargs: Any
) -> list[Evaluation]:
    del kwargs
    return [
        Evaluation(name="turn_accuracy", value=output["turn_accuracy"]),
        Evaluation(name="dialogue_correct", value=output["all_turns_correct"]),
    ]


def aggregate_accuracy_evaluator(
    *, item_results: list[Any], **kwargs: Any
) -> list[Evaluation]:
    del kwargs
    turn_accuracies = [
        evaluation.value
        for result in item_results
        for evaluation in result.evaluations
        if evaluation.name == "turn_accuracy"
    ]
    dialogue_corrects = [
        evaluation.value
        for result in item_results
        for evaluation in result.evaluations
        if evaluation.name == "dialogue_correct"
    ]
    turn_avg = sum(turn_accuracies) / len(turn_accuracies) if turn_accuracies else 0.0
    dialogue_avg = (
        sum(1 for correct in dialogue_corrects if correct) / len(dialogue_corrects)
        if dialogue_corrects
        else 0.0
    )
    return [
        Evaluation(name="avg_turn_accuracy", value=turn_avg),
        Evaluation(name="dialogue_accuracy", value=dialogue_avg),
    ]
