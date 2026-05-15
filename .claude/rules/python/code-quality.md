---
name: code-quality
description: Python code-quality invariants — naming, comments, imports, ruff rules to avoid
paths:
  - backend/src/**
  - backend/tests/**
  - scripts/**
last_validated: 2026-05-15
pillar: true
related:
  - hexagonal
  - tests
---

# Python code quality

## Naming

- Self-explanatory variable names. No underscores in constants or vars: `LITELLM`, never `_LITELLM`.
- snake_case for functions/vars, PascalCase for classes, UPPER for module-level constants.

## Comments

- Default: write none. The code's names do the explaining.
- Allowed only for WHY, never WHAT. If you want to write WHAT, the code is unclear — rewrite it.
- No multi-line docstring blocks. One short line max where strictly necessary.

## Imports

- The installed package is `convfinqa` (wheel ships `backend/src/convfinqa`). ALWAYS import from `convfinqa.*`, NEVER from `backend.src.convfinqa.*` — the latter only resolves under pytest's `pythonpath` and breaks every installed entry point.
- No relative imports across packages. `from ...application.foo import bar` is forbidden.

## Function and module shape

- Zen of Python. Single responsibility. If a function is > 250 lines it's unreadable — split.
- Inject dependencies (see [hexagonal](hexagonal.md)) for testability.
- When a module accumulates helpers, extract them to `utils.py` next to the consumer.

## Ruff rules NOT to enable

- `D101` / `D102` / `D103` (mandatory docstrings) directly contradict the comment policy above. Do not add them to `[tool.ruff.lint.extend-select]`.

## pyproject hygiene

- Do not register a `[project.scripts]` entry for a module that does not exist with a runnable `app` callable. `uv sync` installs the symlink; `uv run <script>` then fails with `ImportError`. Add the entry only when the CLI is real.
