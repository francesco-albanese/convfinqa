- I ABSOLUTELY HATE meaningless tests added only for the sake of increasing the
coverage. I am going to ask you to write in a TDD fashion but silly tests like
for example tests that check if we are able to import modules correctly,
or meaningless tests where we check implementation details MUST be avoided at 
all costs!
- the tests should be written with the user behaviour in mind, always thinking
about how the user would actually use the application for real
- the assertions should be kept to a minimum, only checking the actual logic
and the potential edge cases but WITHOUT EXAGGERATING. Tests should be easy to
read, extra logic for mocking and fixtures and long functions should be 
extracted to a separate file rather than polluting the main test file
- hexagonal architecture should help with mocking, the abstractions will be 
created with the ability to quickly swap a dependency for testing purposes 
without having to do heavy monkey patching. If the implementation is hard-coding
something that could be abstracted away for testing, then do so!

## Async test infrastructure (pytest-asyncio + asyncpg)

- `pyproject.toml` MUST set `asyncio_default_fixture_loop_scope = "session"` under `[tool.pytest.ini_options]`. Without it, pytest-asyncio creates a new event loop per test, and any session-scoped async fixture (e.g. an `AsyncEngine`) gets bound to a different loop than the test consuming it. The symptom is asyncpg raising `InterfaceError: cannot perform operation: another operation is in progress` on the second test.
- Async test fixtures decorated with `@pytest_asyncio.fixture` MUST also pass `loop_scope="session"` (the default is "function").
- Async engines in tests MUST use `poolclass=NullPool`. asyncpg connections are not safe to share across concurrent operations, and SQLAlchemy's default pool will reuse them.
- Per-test isolation comes from the `engine` fixture wiping the tables on setup, NOT from a per-test transactional rollback (asyncpg doesn't compose well with SAVEPOINT-wrapped transactional fixtures).

## Schema setup in tests

- The schema fixture MUST run `alembic upgrade head` against the testcontainer URL, NOT `Base.metadata.create_all`. The PRD calls this out explicitly: catching migration regressions is the whole point of testing against alembic.
- Helper: build an `AlembicConfig` with `script_location` set to `<project_root>/alembic` and `sqlalchemy.url` set to the testcontainer URL, then `command.upgrade(config, "head")`.