from collections.abc import Sequence
from dataclasses import dataclass, field

from convfinqa.application.prompts.sync import PromptSyncEntry, sync_catalog


@dataclass
class FakePublisher:
    stored_hashes: dict[str, str] = field(default_factory=dict[str, str])
    published: list[tuple[str, str, str, list[str]]] = field(
        default_factory=list[tuple[str, str, str, list[str]]]
    )
    next_version: int = 1
    raise_on_fetch: str | None = None
    raise_on_publish: str | None = None

    async def latest_content_hash(self, name: str) -> str | None:
        if self.raise_on_fetch == name:
            raise RuntimeError("langfuse unavailable")
        return self.stored_hashes.get(name)

    async def publish(
        self, name: str, template: str, content_hash: str, labels: Sequence[str]
    ) -> int:
        if self.raise_on_publish == name:
            raise RuntimeError("langfuse write failed")
        self.published.append((name, template, content_hash, list(labels)))
        self.stored_hashes[name] = content_hash
        version = self.next_version
        self.next_version += 1
        return version


async def test_creates_a_new_version_when_content_changed() -> None:
    publisher = FakePublisher()
    entries = [PromptSyncEntry(name="convfinqa-system", template="Hello {{name}}")]

    report = await sync_catalog(entries, publisher, git_sha="abc1234")

    assert report.outcomes[0].status == "created"
    assert report.outcomes[0].version == 1
    assert publisher.published[0][3] == ["latest", "git-abc1234"]
    assert report.has_errors is False


async def test_skips_when_content_hash_is_unchanged() -> None:
    entries = [PromptSyncEntry(name="convfinqa-system", template="Hello {{name}}")]
    publisher = FakePublisher()
    await sync_catalog(entries, publisher, git_sha="abc1234")

    report = await sync_catalog(entries, publisher, git_sha="def5678")

    assert report.outcomes[0].status == "skipped"
    assert len(publisher.published) == 1


async def test_dry_run_reports_intended_change_and_writes_nothing() -> None:
    entries = [PromptSyncEntry(name="convfinqa-system", template="Hello {{name}}")]
    publisher = FakePublisher()

    report = await sync_catalog(entries, publisher, git_sha="abc1234", dry_run=True)

    assert report.outcomes[0].status == "would_create"
    assert publisher.published == []


async def test_fetch_failure_is_reported_as_errored_not_raised() -> None:
    entries = [PromptSyncEntry(name="convfinqa-system", template="Hello {{name}}")]
    publisher = FakePublisher(raise_on_fetch="convfinqa-system")

    report = await sync_catalog(entries, publisher, git_sha="abc1234")

    assert report.outcomes[0].status == "errored"
    assert report.has_errors is True


async def test_publish_failure_is_reported_as_errored_not_raised() -> None:
    entries = [PromptSyncEntry(name="convfinqa-system", template="Hello {{name}}")]
    publisher = FakePublisher(raise_on_publish="convfinqa-system")

    report = await sync_catalog(entries, publisher, git_sha="abc1234")

    assert report.outcomes[0].status == "errored"
    assert report.has_errors is True
