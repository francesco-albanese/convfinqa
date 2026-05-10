from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import cast

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from alembic import command
from convfinqa.adapters.persistence.sqlalchemy.models import Base
from convfinqa.config import Settings
from convfinqa.container import Container
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.entrypoints.api.errors import install_exception_handlers
from convfinqa.entrypoints.api.router import api_router
from tests.fakes.llm import FakeLLMPort

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest_asyncio.fixture(loop_scope="session")
async def engine(database_url: str, schema: None) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(database_url, poolclass=NullPool, future=True)
    async with engine.begin() as conn:
        await conn.execute(Base.metadata.tables["messages"].delete())
        await conn.execute(Base.metadata.tables["conversations"].delete())
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


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
    install_exception_handlers(app)
    app.include_router(router=api_router)
    app.state.container = container

    return app
