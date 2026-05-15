#!/usr/bin/env python3
"""Validate agent-facing knowledge files: .claude/rules/**, **/README.md, CLAUDE.md.

Hard gates (exit 1):
  1. Front-matter schema (rules: name/description/paths/last_validated/related/pillar;
     READMEs: description/last_validated/related).
  2. Path existence (every path/glob in front-matter and every body file reference resolves).
  3. Cross-link integrity (related[] entries resolve to a memory in .claude/memory-index.json
     OR to a file in the repo tree).
  4. Dedup (a rule's name slug must not collide with a memory slug).
  5. Pillar deletion guard (if a pillar:true rule is deleted in HEAD vs BASE_REF, the
     commit message must carry trailer 'Allow-pillar-deletion: <slug>').

Soft gates (warn, exit 0):
  6. Size budget: CLAUDE.md ≤ 50 lines, rule ≤ 100 lines, README ≤ 80 lines.

Modes:
  --changed PATHS...           validate the given files (pre-commit, fast)
  (no args)                    full-repo scan (CI)
  --check-pillar-deletion REF  diff HEAD against REF, enforce pillar trailer rule
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / ".claude" / "rules"
MEMORY_INDEX = REPO_ROOT / ".claude" / "memory-index.json"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

RULE_REQUIRED = ("name", "description", "paths", "last_validated", "related", "pillar")
README_REQUIRED = ("description", "last_validated", "related")
SIZE_BUDGET = {"CLAUDE.md": 50, "rule": 100, "README.md": 80}

FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s#]+)(?:#[^)]*)?\)")


@dataclass
class Finding:
    file: Path
    level: str
    message: str


@dataclass
class Report:
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    def error(self, file: Path, msg: str) -> None:
        self.errors.append(Finding(file, "error", msg))

    def warn(self, file: Path, msg: str) -> None:
        self.warnings.append(Finding(file, "warn", msg))

    def merge(self, other: Report) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def print(self) -> None:
        for f in self.warnings:
            print(f"warn  {f.file.relative_to(REPO_ROOT)}: {f.message}", file=sys.stderr)
        for f in self.errors:
            print(f"error {f.file.relative_to(REPO_ROOT)}: {f.message}", file=sys.stderr)

    @property
    def failed(self) -> bool:
        return bool(self.errors)


def parse_front_matter(text: str) -> tuple[dict[str, Any], str] | None:
    m = FRONT_MATTER_RE.match(text)
    if not m:
        return None
    raw, body = m.group(1), text[m.end() :]
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, []).append(line[4:].strip().strip("\"'"))
        elif ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if not v:
                data[k] = []
                current_key = k
            else:
                data[k] = v.strip("\"'")
                current_key = None
    return data, body


def load_memory_index() -> set[str]:
    if not MEMORY_INDEX.exists():
        return set()
    try:
        raw = json.loads(MEMORY_INDEX.read_text())
    except json.JSONDecodeError:
        return set()
    if isinstance(raw, dict):
        return {k for k in raw if not k.startswith("schema_") and not k.startswith("_")}
    if isinstance(raw, list):
        return {entry.get("name", entry.get("slug", "")) for entry in raw if isinstance(entry, dict)}
    return set()


def parse_iso_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def validate_schema(path: Path, data: dict[str, Any], required: tuple[str, ...], report: Report) -> None:
    for field_name in required:
        if field_name not in data:
            report.error(path, f"missing front-matter field '{field_name}'")
    if "last_validated" in data and parse_iso_date(str(data["last_validated"])) is None:
        report.error(path, f"last_validated '{data['last_validated']}' is not ISO YYYY-MM-DD")
    if "paths" in data and not isinstance(data["paths"], list):
        report.error(path, "paths must be a list")
    if "related" in data and not isinstance(data["related"], list):
        report.error(path, "related must be a list")
    if "pillar" in data and str(data["pillar"]).lower() not in {"true", "false"}:
        report.error(path, f"pillar must be true|false, got {data['pillar']!r}")


def validate_paths_exist(path: Path, data: dict[str, Any], report: Report) -> None:
    for glob_str in data.get("paths", []):
        if not glob_str:
            continue
        matches = list(REPO_ROOT.glob(glob_str))
        if not matches:
            report.error(path, f"paths glob '{glob_str}' matches no files in repo")


def validate_body_references(path: Path, body: str, report: Report) -> None:
    for m in MD_LINK_RE.finditer(body):
        target = m.group(1)
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("/"):
            candidate = REPO_ROOT / target.lstrip("/")
        else:
            candidate = (path.parent / target).resolve()
        if not candidate.exists():
            report.error(path, f"link target '{target}' does not exist")


def validate_related(
    path: Path, data: dict[str, Any], memory_slugs: set[str], rule_slugs: set[str], report: Report
) -> None:
    for entry in data.get("related", []):
        if not entry:
            continue
        if entry in memory_slugs or entry in rule_slugs:
            continue
        candidate_rel = (path.parent / entry).resolve()
        candidate_abs = REPO_ROOT / entry.lstrip("/")
        if candidate_rel.exists() or candidate_abs.exists():
            continue
        report.error(path, f"related entry '{entry}' is neither a memory slug, rule slug, nor existing file")


def validate_size_budget(path: Path, text: str, kind: str, report: Report) -> None:
    limit = SIZE_BUDGET.get(kind)
    if limit is None:
        return
    line_count = text.count("\n") + 1
    if line_count > limit:
        report.warn(path, f"{line_count} lines exceeds {kind} budget of {limit}")


def classify(path: Path) -> str | None:
    rel = path.relative_to(REPO_ROOT)
    if rel.name == "CLAUDE.md":
        return "CLAUDE.md"
    if rel.parts[:2] == (".claude", "rules") and path.suffix == ".md" and path.name != "README.md":
        return "rule"
    if path.name == "README.md":
        return "README.md"
    return None


def validate_file(path: Path, memory_slugs: set[str], rule_slugs: set[str], report: Report) -> None:
    kind = classify(path)
    if kind is None:
        return
    text = path.read_text()
    validate_size_budget(path, text, kind, report)
    parsed = parse_front_matter(text)
    if parsed is None:
        if kind in {"rule", "README.md"}:
            report.error(path, "missing YAML front-matter (--- ... ---)")
        return
    data, body = parsed
    required = RULE_REQUIRED if kind == "rule" else README_REQUIRED if kind == "README.md" else ()
    if required:
        validate_schema(path, data, required, report)
    if kind == "rule":
        name = str(data.get("name", ""))
        if name and name in memory_slugs:
            report.error(path, f"rule name '{name}' collides with a memory slug (dedup violation)")
        if name:
            rule_slugs.add(name)
        validate_paths_exist(path, data, report)
    validate_related(path, data, memory_slugs, rule_slugs, report)
    validate_body_references(path, body, report)


def discover_targets() -> list[Path]:
    targets: list[Path] = []
    if CLAUDE_MD.exists():
        targets.append(CLAUDE_MD)
    if RULES_DIR.exists():
        targets.extend(p for p in RULES_DIR.rglob("*.md"))
    for readme in REPO_ROOT.rglob("README.md"):
        rel_parts = readme.relative_to(REPO_ROOT).parts
        if any(
            part in {"node_modules", ".venv", ".terraform", ".pytest_cache", ".beads", "example-html", ".vite"}
            for part in rel_parts
        ):
            continue
        targets.append(readme)
    return targets


def resolve_pillar_set(at_ref: str | None) -> dict[str, bool]:
    """Map rule-name → pillar bool. If at_ref given, read files from that ref."""
    result: dict[str, bool] = {}
    if at_ref is None:
        for path in RULES_DIR.rglob("*.md"):
            if path.name == "README.md":
                continue
            parsed = parse_front_matter(path.read_text())
            if parsed is None:
                continue
            data, _ = parsed
            name = str(data.get("name", path.stem))
            result[name] = str(data.get("pillar", "false")).lower() == "true"
        return result
    out = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", at_ref, "--", ".claude/rules/"],
        capture_output=True, text=True, cwd=REPO_ROOT, check=False,
    )
    for line in out.stdout.splitlines():
        if not line.endswith(".md") or line.endswith("README.md"):
            continue
        show = subprocess.run(
            ["git", "show", f"{at_ref}:{line}"], capture_output=True, text=True, cwd=REPO_ROOT, check=False,
        )
        if show.returncode != 0:
            continue
        parsed = parse_front_matter(show.stdout)
        if parsed is None:
            continue
        data, _ = parsed
        name = str(data.get("name", Path(line).stem))
        result[name] = str(data.get("pillar", "false")).lower() == "true"
    return result


def check_pillar_deletion(base_ref: str, report: Report) -> None:
    before = resolve_pillar_set(base_ref)
    after = resolve_pillar_set(None)
    deleted_pillars = {name for name, was_pillar in before.items() if was_pillar and name not in after}
    demoted = {name for name, is_pillar in after.items() if name in before and before[name] and not is_pillar}
    if not (deleted_pillars or demoted):
        return
    msg = subprocess.run(
        ["git", "log", f"{base_ref}..HEAD", "--format=%B"], capture_output=True, text=True, cwd=REPO_ROOT, check=False,
    ).stdout
    trailers = {line.split(":", 1)[1].strip() for line in msg.splitlines() if line.startswith("Allow-pillar-deletion:")}
    for slug in deleted_pillars | demoted:
        if slug not in trailers:
            report.error(
                RULES_DIR,
                f"pillar rule '{slug}' deleted, demoted, or renamed without 'Allow-pillar-deletion: {slug}' commit trailer",
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed", nargs="*", help="only validate these files")
    parser.add_argument("--check-pillar-deletion", metavar="REF", help="diff HEAD vs REF for pillar deletions")
    args = parser.parse_args()

    memory_slugs = load_memory_index()
    rule_slugs: set[str] = set()
    if RULES_DIR.exists():
        for rule_path in RULES_DIR.rglob("*.md"):
            if rule_path.name == "README.md":
                continue
            parsed = parse_front_matter(rule_path.read_text())
            if parsed is None:
                continue
            name = str(parsed[0].get("name", "")).strip()
            if name:
                rule_slugs.add(name)
    report = Report()

    if args.changed:
        targets = [Path(p).resolve() for p in args.changed if Path(p).exists()]
    else:
        targets = discover_targets()

    for path in targets:
        try:
            path.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if classify(path) is None:
            continue
        validate_file(path, memory_slugs, rule_slugs, report)

    if args.check_pillar_deletion:
        check_pillar_deletion(args.check_pillar_deletion, report)

    report.print()
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
