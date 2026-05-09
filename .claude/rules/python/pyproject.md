# pyproject.toml rules

## Console scripts

Never register a `[project.scripts]` entry whose target module is empty or non-existent. `uv sync` will install the script symlink, and any subsequent `uv run <script>` will fail with `ImportError`. If a CLI is planned but not yet implemented, leave the entry out until the module exists with a runnable `app` callable.

## Linter rules vs project comment policy

The project rule (`.claude/rules/python/comments.md`) says: do not write WHAT comments. Forcing docstrings on every public function/method (ruff codes `D101`/`D102`/`D103`) directly contradicts that — those rules require WHAT-style docstrings. Do NOT add `D101`/`D102`/`D103` to `[tool.ruff.lint.extend-select]`.

## Postgres image pin

`docker-compose.yml` uses `postgres:18.3-bookworm`. Do not change to `latest`, bare `18.3`, `trixie`, or `alpine`:
- `latest` — moves with releases, breaks reproducibility.
- bare `18.3` — Postgres' default Debian base; today bookworm but upstream may flip.
- `trixie` — Debian 13 stabilised mid-2025; less mileage with asyncpg.
- `alpine` — musl libc; occasional asyncpg/locale edge cases.

Bookworm = Debian 12, what testcontainers + most CI image stacks use, max reproducibility.
