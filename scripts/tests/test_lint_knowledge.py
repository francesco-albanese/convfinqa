"""Tests for scripts/lint_knowledge.py."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_SCRIPT = Path(__file__).parent.parent / "lint_knowledge.py"


def _load() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("lint_knowledge", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lint_knowledge"] = mod  # required for dataclass decorator resolution
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


lk = _load()


# ---------------------------------------------------------------------------
# parse_front_matter
# ---------------------------------------------------------------------------


def test_parse_front_matter_no_front_matter() -> None:
    assert lk.parse_front_matter("no front matter\n") is None


def test_parse_front_matter_unclosed_delimiter() -> None:
    assert lk.parse_front_matter("---\nname: foo\n") is None


def test_parse_front_matter_single_quote_trailing_edge() -> None:
    text = "---\nname: 'my-rule'\n---\nbody\n"
    result = lk.parse_front_matter(text)
    assert result is not None
    data, body = result
    assert data["name"] == "my-rule"
    assert "body" in body


def test_parse_front_matter_list_with_empty_item() -> None:
    text = "---\nrelated:\n  - \n  - foo\n---\nbody\n"
    result = lk.parse_front_matter(text)
    assert result is not None
    data, _ = result
    assert "foo" in data["related"]
    assert "" in data["related"]


def test_parse_front_matter_crlf_returns_none() -> None:
    # CRLF endings break the \A---\n regex — returns None gracefully
    text = "---\r\nname: foo\r\n---\r\nbody\r\n"
    assert lk.parse_front_matter(text) is None


# ---------------------------------------------------------------------------
# validate_paths_exist
# ---------------------------------------------------------------------------


def test_validate_paths_exist_matching_glob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lk, "REPO_ROOT", tmp_path)
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "main.py").write_text("")
    rule = tmp_path / "rule.md"
    rule.write_text("")
    report = lk.Report()
    lk.validate_paths_exist(rule, {"paths": ["backend/*.py"]}, report)
    assert not report.errors


def test_validate_paths_exist_no_match_reports_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lk, "REPO_ROOT", tmp_path)
    rule = tmp_path / "rule.md"
    rule.write_text("")
    report = lk.Report()
    lk.validate_paths_exist(rule, {"paths": ["nonexistent/**/*.py"]}, report)
    assert len(report.errors) == 1
    assert "nonexistent/**/*.py" in report.errors[0].message


# ---------------------------------------------------------------------------
# validate_related
# ---------------------------------------------------------------------------


def test_validate_related_memory_slug_passes(tmp_path: Path) -> None:
    rule = tmp_path / "rule.md"
    rule.write_text("")
    report = lk.Report()
    lk.validate_related(rule, {"related": ["some-memory"]}, {"some-memory"}, set(), report)
    assert not report.errors


def test_validate_related_rule_slug_passes(tmp_path: Path) -> None:
    rule = tmp_path / "rule.md"
    rule.write_text("")
    report = lk.Report()
    lk.validate_related(rule, {"related": ["other-rule"]}, set(), {"other-rule"}, report)
    assert not report.errors


def test_validate_related_file_path_passes(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("")
    rule = tmp_path / "rule.md"
    rule.write_text("")
    report = lk.Report()
    lk.validate_related(rule, {"related": ["docs/guide.md"]}, set(), set(), report)
    assert not report.errors


def test_validate_related_all_miss_reports_error(tmp_path: Path) -> None:
    rule = tmp_path / "rule.md"
    rule.write_text("")
    report = lk.Report()
    lk.validate_related(rule, {"related": ["no-such-thing"]}, set(), set(), report)
    assert len(report.errors) == 1
    assert "no-such-thing" in report.errors[0].message


# ---------------------------------------------------------------------------
# check_pillar_deletion
# ---------------------------------------------------------------------------


def _pillar_md(name: str, *, is_pillar: bool) -> str:
    flag = "true" if is_pillar else "false"
    return (
        f"---\nname: {name}\ndescription: test\npaths:\n"
        f"last_validated: 2026-01-01\nrelated:\npillar: {flag}\n---\nbody\n"
    )


def _fake_subprocess(ls_tree: str, show: str, log: str) -> MagicMock:
    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        result = MagicMock()
        result.returncode = 0
        if "ls-tree" in cmd:
            result.stdout = ls_tree
        elif "show" in cmd:
            result.stdout = show
        elif "log" in cmd:
            result.stdout = log
        else:
            result.stdout = ""
        return result

    mock = MagicMock()
    mock.run = fake_run
    return mock


def test_check_pillar_deletion_without_trailer_reports_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    monkeypatch.setattr(lk, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lk, "RULES_DIR", rules_dir)
    monkeypatch.setattr(
        lk,
        "subprocess",
        _fake_subprocess(
            ls_tree=".claude/rules/old.md\n",
            show=_pillar_md("core-pillar", is_pillar=True),
            log="feat: remove pillar\n",
        ),
    )
    report = lk.Report()
    lk.check_pillar_deletion("main", report)
    assert any("core-pillar" in e.message for e in report.errors)


def test_check_pillar_deletion_with_trailer_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    monkeypatch.setattr(lk, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lk, "RULES_DIR", rules_dir)
    monkeypatch.setattr(
        lk,
        "subprocess",
        _fake_subprocess(
            ls_tree=".claude/rules/old.md\n",
            show=_pillar_md("core-pillar", is_pillar=True),
            log="feat: remove pillar\n\nAllow-pillar-deletion: core-pillar\n",
        ),
    )
    report = lk.Report()
    lk.check_pillar_deletion("main", report)
    assert not report.errors


def test_check_pillar_deletion_rename_treated_as_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    # HEAD has "new-pillar" (rename) — "old-pillar" is missing → treated as deletion
    (rules_dir / "new-pillar.md").write_text(_pillar_md("new-pillar", is_pillar=True))
    monkeypatch.setattr(lk, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lk, "RULES_DIR", rules_dir)
    monkeypatch.setattr(
        lk,
        "subprocess",
        _fake_subprocess(
            ls_tree=".claude/rules/old-pillar.md\n",
            show=_pillar_md("old-pillar", is_pillar=True),
            log="refactor: rename pillar\n",
        ),
    )
    report = lk.Report()
    lk.check_pillar_deletion("main", report)
    assert any("old-pillar" in e.message for e in report.errors)
