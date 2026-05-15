---
name: tests
description: Test-writing rules — user-behaviour focus, async pytest-asyncio infra, alembic-driven schema fixtures
paths:
  - backend/tests/**
last_validated: 2026-05-15
pillar: true
related:
  - hexagonal
  - asyncpg-pytest-asyncio-cannot-perform-operation-another-oper
  - pytest-marker-auto-tag-pattern-extract-the-path
---

# Testing rules

## What to test

- Write tests for **user behaviour**, not implementation details. The mental model is "how would this actually be used?"
- Keep assertions minimal — the actual logic and the real edge cases. No tests that exist solely for coverage. No "module imports correctly" tests.
- Tests should be easy to read. Long fixtures / heavy mocking belong in a separate file, not the test body.
- Hexagonal architecture is your friend: ports make dependency swap trivial without monkey-patching.

## Async test infrastructure (pytest-asyncio + asyncpg)

- `[tool.pytest.ini_options] asyncio_default_fixture_loop_scope = "session"` — without it, every test gets a new event loop and any session-scoped async fixture (`AsyncEngine`) ends up on a different loop than the test. Symptom: asyncpg `InterfaceError: cannot perform operation: another operation is in progress` on the second test.
- `@pytest_asyncio.fixture` MUST also pass `loop_scope="session"` (default is `"function"`).
- Test engines MUST use `poolclass=NullPool`. asyncpg connections aren't safe to share across concurrent ops; the default pool reuses them.
- Per-test isolation: wipe tables in the `engine` fixture setup, NOT via per-test transactional rollback (asyncpg + SAVEPOINT compose poorly).

## Schema setup

The schema fixture MUST run `alembic upgrade head` against the testcontainer URL, NOT `Base.metadata.create_all`. Catching migration regressions is the entire point of testing against alembic.

Helper: build an `AlembicConfig` with `script_location = <repo>/alembic` and `sqlalchemy.url = <testcontainer URL>`, then `command.upgrade(config, "head")`.
