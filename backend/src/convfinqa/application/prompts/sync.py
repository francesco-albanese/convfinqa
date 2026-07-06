import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from convfinqa.domain.ports.prompts import PromptPublisherPort

SyncStatus = Literal["created", "would_create", "skipped", "errored"]


@dataclass(frozen=True, slots=True)
class PromptSyncEntry:
    name: str
    template: str


@dataclass(frozen=True, slots=True)
class SyncOutcome:
    name: str
    status: SyncStatus
    version: int | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SyncReport:
    outcomes: tuple[SyncOutcome, ...]

    @property
    def has_errors(self) -> bool:
        return any(outcome.status == "errored" for outcome in self.outcomes)


def content_hash(template: str) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()


async def sync_catalog(
    entries: Sequence[PromptSyncEntry],
    publisher: PromptPublisherPort,
    git_sha: str,
    *,
    dry_run: bool = False,
) -> SyncReport:
    outcomes = [
        await _sync_entry(entry, publisher, git_sha, dry_run=dry_run)
        for entry in entries
    ]
    return SyncReport(tuple(outcomes))


async def _sync_entry(
    entry: PromptSyncEntry,
    publisher: PromptPublisherPort,
    git_sha: str,
    *,
    dry_run: bool,
) -> SyncOutcome:
    new_hash = content_hash(entry.template)
    try:
        previous_hash = await publisher.latest_content_hash(entry.name)
    except Exception as exc:  # noqa: BLE001
        return SyncOutcome(entry.name, "errored", error=str(exc))

    if previous_hash == new_hash:
        return SyncOutcome(entry.name, "skipped")

    if dry_run:
        return SyncOutcome(entry.name, "would_create")

    try:
        version = await publisher.publish(
            entry.name,
            entry.template,
            new_hash,
            labels=["latest", f"git-{git_sha}"],
        )
    except Exception as exc:  # noqa: BLE001
        return SyncOutcome(entry.name, "errored", error=str(exc))

    return SyncOutcome(entry.name, "created", version=version)
