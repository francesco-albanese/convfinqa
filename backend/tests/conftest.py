from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import cast

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from convfinqa.adapters.persistence.sqlalchemy.models import Base
from convfinqa.config import Settings
from convfinqa.container import Container
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.entrypoints.api.errors import install_exception_handlers
from convfinqa.entrypoints.api.middleware.auth import AuthMiddleware
from convfinqa.entrypoints.api.router import api_router
from tests.fakes.llm import FakeLLMPort
from tests.marker_policy import apply_path_markers, unmarked_node_ids

pytest_plugins = ["pytester"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = Path(__file__).resolve().parent

DEFAULT_DOCUMENT_ID = "Single_TEST/2024/page_1.pdf-1"
SEEDED_USER_UUID = "00000000-0000-0000-0000-000000000001"


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    apply_path_markers(items, TESTS_DIR)
    unmarked = unmarked_node_ids(items)
    if unmarked:
        raise pytest.UsageError(
            f"Unmarked tests: {unmarked}. "
            "Add a path mapping in backend/tests/marker_policy.py "
            "or set pytestmark = pytest.mark.unit|integration."
        )


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    with PostgresContainer("postgres:18.3-bookworm", driver="asyncpg") as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url(postgres_container: PostgresContainer) -> str:
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def schema(database_url: str) -> None:
    config = AlembicConfig(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest_asyncio.fixture(loop_scope="session")
async def engine(database_url: str, schema: None) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(database_url, poolclass=NullPool, future=True)
    async with engine.begin() as conn:
        await conn.execute(Base.metadata.tables["messages"].delete())
        await conn.execute(Base.metadata.tables["conversations"].delete())
        await conn.execute(Base.metadata.tables["documents"].delete())
        await conn.execute(
            text(
                "INSERT INTO documents "
                "(id, ticker, year, page, title, pre_text, post_text, "
                "table_data, column_order) "
                "VALUES "
                "(:id, :ticker, :year, :page, :title, :pre_text, "
                ":post_text, CAST(:table_data AS jsonb), :column_order)"
            ),
            {
                "id": DEFAULT_DOCUMENT_ID,
                "ticker": "TEST",
                "year": 2024,
                "page": 1,
                "title": "TEST 2024 annual report",
                "pre_text": "fixture pre-text",
                "post_text": "fixture post-text",
                "table_data": '{"revenue": [100, 200]}',
                "column_order": ["revenue"],
            },
        )
        await conn.execute(
            text(
                "INSERT INTO users (id, cognito_sub, email) "
                "VALUES (CAST(:id AS uuid), :sub, :email) "
                "ON CONFLICT (cognito_sub) DO NOTHING"
            ),
            {
                "id": SEEDED_USER_UUID,
                "sub": "test-cognito-sub",
                "email": "test@example.com",
            },
        )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def seeded_document_id() -> str:
    return DEFAULT_DOCUMENT_ID


@pytest.fixture
def seeded_user_id() -> str:
    return SEEDED_USER_UUID


@pytest.fixture
def fake_llm() -> FakeLLMPort:
    return FakeLLMPort()


@pytest_asyncio.fixture(loop_scope="session")
async def app(
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
    fake_llm: FakeLLMPort,
) -> FastAPI:
    settings = Settings()
    container = Container.for_testing(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        llm=cast(LLMPort, fake_llm),
    )

    app = FastAPI(title="convfinqa-test")
    app.add_middleware(AuthMiddleware)
    install_exception_handlers(app)
    app.include_router(router=api_router)
    app.state.container = container

    return app
