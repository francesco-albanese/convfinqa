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
from convfinqa.config import Settings

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
