from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from convfinqa.config import SETTINGS
from convfinqa.container import Container
from convfinqa.entrypoints.api.errors import install_exception_handlers
from convfinqa.entrypoints.api.router import api_router
from convfinqa.logging import configure_logging


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

def serve_app() -> None:
    uvicorn.run(
        "convfinqa.main:create_app",
        factory=True,
        host=SETTINGS.api_host,
        port=SETTINGS.api_port,
        reload=SETTINGS.api_reload
    )
