from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.convfinqa.config import SETTINGS
from src.convfinqa.container import Container
from src.convfinqa.entrypoints.api.errors import install_exception_handlers
from src.convfinqa.entrypoints.api.router import api_router
from src.convfinqa.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container = Container.bootstrap_application(settings=SETTINGS)
    app.state.container = container
    try:
        yield
    finally:
        await container.engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="convfinqa", lifespan=lifespan)
    install_exception_handlers(app)
    app.include_router(router=api_router)
    return app
