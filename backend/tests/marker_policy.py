from collections.abc import Iterable
from pathlib import Path
from typing import Final

import pytest

PATH_MARKERS: Final[dict[str, str]] = {
    "api": "integration",
    "entrypoints/api": "integration",
    "adapters": "integration",
    "integration": "integration",
    "cli": "unit",
    "entrypoints/cli": "unit",
    "domain": "unit",
    "application": "unit",
    "fakes": "unit",
    "security": "unit",
    "unit": "unit",
}


def apply_path_markers(items: Iterable[pytest.Item], tests_dir: Path) -> None:
    sorted_prefixes = sorted(PATH_MARKERS.items(), key=lambda kv: -len(kv[0]))
    for item in items:
        if item.get_closest_marker("unit") or item.get_closest_marker("integration"):
            continue
        try:
            relative = item.path.relative_to(tests_dir)
        except ValueError:
            continue
        rel_dir = str(relative.parent).replace("\\", "/")
        for prefix, marker_name in sorted_prefixes:
            if rel_dir == prefix or rel_dir.startswith(prefix + "/"):
                marker = (
                    pytest.mark.unit
                    if marker_name == "unit"
                    else pytest.mark.integration
                )
                item.add_marker(marker)
                break


def unmarked_node_ids(items: Iterable[pytest.Item]) -> list[str]:
    return [
        item.nodeid
        for item in items
        if not item.get_closest_marker("unit")
        and not item.get_closest_marker("integration")
    ]
