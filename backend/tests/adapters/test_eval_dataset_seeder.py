import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langfuse.api.commons.errors.not_found_error import NotFoundError

from convfinqa.adapters.eval.dataset_seeder import iter_dialogue_items, seed


def _build_dataset(tmp_path: Path) -> Path:
    dataset: dict[str, list[dict[str, Any]]] = {
        "train": [
            {
                "id": "Single_JKHY/2009/page_28.pdf-3",
                "doc": {"pre_text": "", "post_text": "", "table": {}},
                "dialogue": {
                    "conv_questions": [
                        "what is the net cash from operating activities in 2009?",
                        "what about in 2008?",
                    ],
                    "conv_answers": ["206588", "181001"],
                    "turn_program": ["206588", "181001"],
                    "executed_answers": [206588.0, 181001.0],
                },
            }
        ],
        "dev": [
            {
                "id": "Single_SEEDB/2020/page_5.pdf-1",
                "doc": {"pre_text": "", "post_text": "", "table": {}},
                "dialogue": {
                    "conv_questions": ["what was revenue?"],
                    "conv_answers": ["100"],
                    "turn_program": ["100"],
                    "executed_answers": [100.0],
                },
            }
        ],
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset))
    return path


def test_iter_dialogue_items_maps_ordered_questions_and_answers(
    tmp_path: Path,
) -> None:
    items = list(iter_dialogue_items(_build_dataset(tmp_path)))

    assert {item.id for item in items} == {
        "Single_JKHY/2009/page_28.pdf-3",
        "Single_SEEDB/2020/page_5.pdf-1",
    }
    jkhy = next(i for i in items if i.id == "Single_JKHY/2009/page_28.pdf-3")
    assert jkhy.questions == [
        "what is the net cash from operating activities in 2009?",
        "what about in 2008?",
    ]
    assert jkhy.expected_output == ["206588", "181001"]
    assert jkhy.executed_answers == [206588.0, 181001.0]
    assert jkhy.turn_program == ["206588", "181001"]


def test_iter_dialogue_items_defaults_to_empty_when_dialogue_missing(
    tmp_path: Path,
) -> None:
    dataset: dict[str, list[dict[str, Any]]] = {
        "train": [
            {"id": "Single_NODLG/2020/page_1.pdf-1", "doc": {}},
        ],
        "dev": [],
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset))

    item = next(iter_dialogue_items(path))

    assert item.questions == []
    assert item.expected_output == []


@dataclass
class FakeDataset:
    exists: bool = False


@dataclass
class FakeLangfuseClient:
    datasets: dict[str, FakeDataset] = field(default_factory=dict[str, FakeDataset])
    items: dict[str, dict[str, Any]] = field(default_factory=dict[str, dict[str, Any]])
    dataset_create_calls: int = 0

    def get_dataset(self, name: str) -> FakeDataset:
        if name not in self.datasets:
            raise NotFoundError(body="not found")
        return self.datasets[name]

    def create_dataset(self, *, name: str) -> FakeDataset:
        self.dataset_create_calls += 1
        dataset = FakeDataset(exists=True)
        self.datasets[name] = dataset
        return dataset

    def create_dataset_item(
        self,
        *,
        dataset_name: str,
        id: str,
        input: Any,
        expected_output: Any,
        metadata: Any,
    ) -> None:
        self.items[id] = {
            "dataset_name": dataset_name,
            "input": input,
            "expected_output": expected_output,
            "metadata": metadata,
        }


async def test_seed_creates_dataset_once_and_one_item_per_dialogue(
    tmp_path: Path,
) -> None:
    client = FakeLangfuseClient()
    dataset_path = _build_dataset(tmp_path)

    total = await seed(client, dataset_path, "convfinqa-dialogues")

    assert total == 2
    assert client.dataset_create_calls == 1
    assert set(client.items) == {
        "Single_JKHY/2009/page_28.pdf-3",
        "Single_SEEDB/2020/page_5.pdf-1",
    }
    jkhy_item = client.items["Single_JKHY/2009/page_28.pdf-3"]
    assert jkhy_item["expected_output"] == ["206588", "181001"]
    assert jkhy_item["metadata"]["executed_answers"] == [206588.0, 181001.0]
    assert jkhy_item["metadata"]["turn_program"] == ["206588", "181001"]


async def test_seed_is_idempotent_and_does_not_recreate_dataset(
    tmp_path: Path,
) -> None:
    client = FakeLangfuseClient()
    dataset_path = _build_dataset(tmp_path)

    await seed(client, dataset_path, "convfinqa-dialogues")
    await seed(client, dataset_path, "convfinqa-dialogues")

    assert client.dataset_create_calls == 1
    assert len(client.items) == 2
