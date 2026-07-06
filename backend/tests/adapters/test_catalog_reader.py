from convfinqa.adapters.prompts.catalog_reader import read_catalog_entries


def test_reads_the_committed_catalog_entries() -> None:
    entries = read_catalog_entries()

    names = [entry.name for entry in entries]
    assert "convfinqa-system" in names
    assert "convfinqa-title" in names

    system_entry = next(entry for entry in entries if entry.name == "convfinqa-system")
    assert "{{" in system_entry.template

    title_entry = next(entry for entry in entries if entry.name == "convfinqa-title")
    assert "title" in title_entry.template.lower()


def test_entries_are_sorted_by_name() -> None:
    entries = read_catalog_entries()

    names = [entry.name for entry in entries]
    assert names == sorted(names)
