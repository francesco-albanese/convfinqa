from dataclasses import dataclass
from typing import Any

from langfuse import Evaluation

from convfinqa.adapters.eval.experiment_glue import (
    aggregate_accuracy_evaluator,
    build_task,
    turn_accuracy_evaluator,
)
from tests.application.send_message_fakes import (
    FakeConvRepo,
    FakeDocRepo,
    FakeLLM,
    build_use_case,
    document,
)


@dataclass
class FakeDatasetItem:
    input: dict[str, Any]
    expected_output: list[str]


async def test_build_task_replays_dialogue_and_reports_turn_shape() -> None:
    convs = FakeConvRepo()
    docs = FakeDocRepo(by_id={"doc-1": document()})
    llm = FakeLLM(deltas=("206588 in the pinned document.",))
    use_case = build_use_case(convs, docs, llm)
    item = FakeDatasetItem(
        input={
            "document_id": "doc-1",
            "questions": ["what was revenue in the pinned document?"],
        },
        expected_output=["206588"],
    )

    task = build_task(use_case, model=None)
    output = await task(item=item)

    assert output["turn_accuracy"] == 1.0
    assert output["all_turns_correct"] is True
    assert len(output["turns"]) == 1
    assert output["turns"][0]["passed"] is True


def test_turn_accuracy_evaluator_maps_output_fields_to_evaluations() -> None:
    evaluations = turn_accuracy_evaluator(
        output={"turn_accuracy": 0.5, "all_turns_correct": False}
    )

    values = {e.name: e.value for e in evaluations}
    assert values == {"turn_accuracy": 0.5, "dialogue_correct": False}


def test_aggregate_accuracy_evaluator_averages_across_items() -> None:
    @dataclass
    class FakeItemResult:
        evaluations: list[Evaluation]

    item_results = [
        FakeItemResult(
            evaluations=[
                Evaluation(name="turn_accuracy", value=1.0),
                Evaluation(name="dialogue_correct", value=True),
            ]
        ),
        FakeItemResult(
            evaluations=[
                Evaluation(name="turn_accuracy", value=0.0),
                Evaluation(name="dialogue_correct", value=False),
            ]
        ),
    ]

    evaluations = aggregate_accuracy_evaluator(item_results=item_results)

    values = {e.name: e.value for e in evaluations}
    assert values == {"avg_turn_accuracy": 0.5, "dialogue_accuracy": 0.5}


def test_aggregate_accuracy_evaluator_handles_empty_results() -> None:
    evaluations = aggregate_accuracy_evaluator(item_results=[])

    values = {e.name: e.value for e in evaluations}
    assert values == {"avg_turn_accuracy": 0.0, "dialogue_accuracy": 0.0}
