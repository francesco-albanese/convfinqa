from importlib import resources

from convfinqa.application.prompts.sync import PromptSyncEntry

CATALOG_LABEL = "production"


def read_catalog_entries(
    package: str = "convfinqa.adapters.prompts.catalog",
) -> tuple[PromptSyncEntry, ...]:
    suffix = f".{CATALOG_LABEL}.md"
    entries = [
        PromptSyncEntry(
            name=item.name.removesuffix(suffix),
            template=item.read_text(encoding="utf-8"),
        )
        for item in resources.files(package).iterdir()
        if item.is_file() and item.name.endswith(suffix)
    ]
    return tuple(sorted(entries, key=lambda entry: entry.name))
