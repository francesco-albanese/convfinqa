import asyncio
import sys
from typing import Annotated

import typer
from langfuse import Langfuse

from convfinqa.adapters.eval.dataset_seeder import (
    DEFAULT_DATASET_NAME,
    resolve_dataset_path,
    seed,
)
from convfinqa.adapters.eval.experiment_glue import (
    aggregate_accuracy_evaluator,
    build_task,
    turn_accuracy_evaluator,
)
from convfinqa.config import Settings
from convfinqa.container import bootstrap_application

eval_app = typer.Typer(no_args_is_help=True, add_completion=False)


@eval_app.command(name="seed-dataset")
def seed_dataset(
    dataset_name: Annotated[
        str,
        typer.Option("--dataset-name", help="Langfuse dataset name."),
    ] = DEFAULT_DATASET_NAME,
) -> None:
    """Seed a Langfuse dataset with one item per ConvFinQA dialogue."""
    settings = Settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        sys.stdout.write(
            "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set; nothing to seed.\n"
        )
        raise typer.Exit(code=1)

    dataset_path = resolve_dataset_path()
    if not dataset_path.is_file():
        sys.stdout.write(f"dataset file not found: {dataset_path}\n")
        raise typer.Exit(code=1)

    client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        tracing_enabled=False,
    )
    total = asyncio.run(seed(client, dataset_path, dataset_name))
    sys.stdout.write(f"seeded {total} dialogue items into dataset {dataset_name!r}\n")


@eval_app.command(name="run")
def run(
    prompt_label: Annotated[
        str,
        typer.Option(
            "--prompt-label", help="Langfuse prompt label to serve, e.g. 'latest'."
        ),
    ] = "production",
    dataset_name: Annotated[
        str,
        typer.Option("--dataset", help="Langfuse dataset name to replay."),
    ] = DEFAULT_DATASET_NAME,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Override the LLM model for this run."),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit", help="Cap the number of dialogues replayed (default: all)."
        ),
    ] = None,
) -> None:
    """Replay a Langfuse dataset through the real agent and score it."""
    settings = Settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        sys.stdout.write(
            "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set; nothing to run.\n"
        )
        raise typer.Exit(code=1)

    client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        tracing_enabled=False,
    )
    dataset = client.get_dataset(dataset_name)
    items = list(dataset.items)[:limit] if limit is not None else list(dataset.items)
    if not items:
        sys.stdout.write(f"dataset {dataset_name!r} has no items to replay.\n")
        raise typer.Exit(code=1)

    container = bootstrap_application(settings, system_prompt_label=prompt_label)
    try:
        result = client.run_experiment(
            name=f"convfinqa-eval-{prompt_label}",
            data=items,
            task=build_task(container.send_message, model),
            evaluators=[turn_accuracy_evaluator],
            run_evaluators=[aggregate_accuracy_evaluator],
            metadata={"prompt_label": prompt_label, "model": model or settings.llm_model},
        )
    finally:
        try:
            asyncio.run(container.engine.dispose())
        except Exception:  # noqa: BLE001
            pass

    sys.stdout.write(f"dataset run: {result.run_name}\n")
    if result.dataset_run_url:
        sys.stdout.write(f"view results: {result.dataset_run_url}\n")
    for run_evaluation in result.run_evaluations:
        sys.stdout.write(f"{run_evaluation.name}: {run_evaluation.value}\n")
