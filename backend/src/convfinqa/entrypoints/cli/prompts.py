import asyncio
import subprocess
import sys
from typing import Annotated

import typer
from langfuse import Langfuse

from convfinqa.adapters.prompts.catalog_reader import read_catalog_entries
from convfinqa.adapters.prompts.langfuse_publisher import LangfusePromptPublisher
from convfinqa.application.prompts.sync import SyncReport, sync_catalog
from convfinqa.config import Settings

prompts_app = typer.Typer(no_args_is_help=True, add_completion=False)


def _git_short_sha() -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _print_report(report: SyncReport, *, dry_run: bool) -> None:
    for outcome in report.outcomes:
        if outcome.status == "created":
            sys.stdout.write(f"created  {outcome.name} -> version {outcome.version}\n")
        elif outcome.status == "would_create":
            sys.stdout.write(f"would create  {outcome.name} (dry-run)\n")
        elif outcome.status == "skipped":
            sys.stdout.write(f"skipped  {outcome.name} (unchanged)\n")
        else:
            sys.stdout.write(f"errored  {outcome.name}: {outcome.error}\n")

    if dry_run:
        sys.stdout.write("dry-run: no changes were written\n")


@prompts_app.command(name="sync")
def sync(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Report intended changes without publishing."),
    ] = False,
) -> None:
    """Publish the git-committed prompt catalog to Langfuse."""
    settings = Settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        sys.stdout.write(
            "LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set; nothing to sync.\n"
        )
        raise typer.Exit(code=1)

    client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        tracing_enabled=False,
    )
    publisher = LangfusePromptPublisher(client)
    entries = read_catalog_entries()
    git_sha = _git_short_sha()

    report = asyncio.run(sync_catalog(entries, publisher, git_sha, dry_run=dry_run))
    _print_report(report, dry_run=dry_run)

    if report.has_errors:
        raise typer.Exit(code=1)
