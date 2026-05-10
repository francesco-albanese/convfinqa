import pytest

pytestmark = pytest.mark.unit


SYNTHETIC_CONFTEST = """
from pathlib import Path
import pytest
from tests.marker_policy import apply_path_markers, unmarked_node_ids


def pytest_collection_modifyitems(config, items):
    apply_path_markers(items, Path(__file__).parent)
    unmarked = unmarked_node_ids(items)
    if unmarked:
        raise pytest.UsageError(f"Unmarked tests: {unmarked}")
"""

SYNTHETIC_INI = """
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
markers =
    unit: u
    integration: i
"""


def test_unmapped_path_fails_collection(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(SYNTHETIC_CONFTEST)
    pytester.makeini(SYNTHETIC_INI)

    unmapped = pytester.mkdir("unmapped")
    (unmapped / "test_orphan.py").write_text("def test_a(): pass\n")

    result = pytester.runpytest("--collect-only")

    assert result.ret != 0
    output = "\n".join(result.outlines + result.errlines)
    assert "Unmarked tests" in output
    assert "test_orphan" in output


def test_mapped_path_passes_collection(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(SYNTHETIC_CONFTEST)
    pytester.makeini(SYNTHETIC_INI)

    cli_dir = pytester.mkdir("cli")
    (cli_dir / "test_thing.py").write_text("def test_a(): pass\n")

    result = pytester.runpytest("--collect-only", "-m", "unit")

    assert result.ret == 0
    output = "\n".join(result.outlines)
    assert "test_thing" in output
