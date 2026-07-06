import asyncio
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from langfuse import Langfuse
from langfuse.api.commons.errors.not_found_error import NotFoundError

from convfinqa.config import Settings
from convfinqa.logging import get_logger

LOGGER = get_logger("convfinqa.eval_seed")

DEFAULT_DATASET_NAME = "convfinqa-dialogues"


@dataclass(frozen=True, slots=True)
class DialogueItem:
    id: str
    document_id: str
    questions: list[str]
    expected_output: list[str]
    executed_answers: list[float | None]
    turn_program: list[str]


def iter_dialogue_items(dataset_path: Path) -> Iterator[DialogueItem]:
    with dataset_path.open(encoding="utf-8") as fp:
        data: dict[str, list[dict[str, Any]]] = json.load(fp)

    for split in ("train", "dev"):
        for raw_record in data.get(split, []):
            document_id = raw_record["id"]
            dialogue: dict[str, Any] = raw_record.get("dialogue") or {}
            yield DialogueItem(
                id=document_id,
                document_id=document_id,
                questions=list(dialogue.get("conv_questions", [])),
                expected_output=list(dialogue.get("conv_answers", [])),
                executed_answers=list(dialogue.get("executed_answers", [])),
                turn_program=list(dialogue.get("turn_program", [])),
            )


class _LangfuseClient(Protocol):
    def get_dataset(self, name: str) -> Any: ...

    def create_dataset(self, *, name: str) -> Any: ...

    def create_dataset_item(
        self,
        *,
        dataset_name: str,
        id: str,
        input: Any,
        expected_output: Any,
        metadata: Any,
    ) -> Any: ...


async def ensure_dataset(client: Any, name: str) -> None:
    typed_client = cast("_LangfuseClient", client)

    def _ensure() -> None:
        try:
            typed_client.get_dataset(name)
        except NotFoundError:
            typed_client.create_dataset(name=name)

    await asyncio.to_thread(_ensure)


async def seed_item(client: Any, dataset_name: str, item: DialogueItem) -> None:
    typed_client = cast("_LangfuseClient", client)

    def _create() -> None:
        typed_client.create_dataset_item(
            dataset_name=dataset_name,
            id=item.id,
            input={"document_id": item.document_id, "questions": item.questions},
            expected_output=item.expected_output,
            metadata={
                "executed_answers": item.executed_answers,
                "turn_program": item.turn_program,
            },
        )

    await asyncio.to_thread(_create)


async def seed(
    client: Any, dataset_path: Path, dataset_name: str = DEFAULT_DATASET_NAME
) -> int:
    await ensure_dataset(client, dataset_name)
    total = 0
    for item in iter_dialogue_items(dataset_path):
        await seed_item(client, dataset_name, item)
        total += 1
    return total


def resolve_dataset_path() -> Path:
    explicit = os.getenv("CONVFINQA_DATASET_PATH")
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "convfinqa_dataset.json"
        if candidate.is_file():
            return candidate
    return Path("data/convfinqa_dataset.json")


def main() -> int:
    settings = Settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        LOGGER.error("langfuse_keys_not_configured")
        return 1

    dataset_path = resolve_dataset_path()
    if not dataset_path.is_file():
        LOGGER.error(
            "dataset_file_not_found", extra={"dataset_path": str(dataset_path)}
        )
        return 1

    client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        tracing_enabled=False,
    )
    total = asyncio.run(seed(client, dataset_path))
    LOGGER.info(
        "eval_dataset_seeded",
        extra={"items_upserted": total, "dataset_path": str(dataset_path)},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
