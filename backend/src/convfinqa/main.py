from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from convfinqa.adapters.observability.instrumentation import (
    register_auto_instrumentations,
)
from convfinqa.config import SETTINGS
from convfinqa.container import bootstrap_application
from convfinqa.entrypoints.api.errors import install_exception_handlers
from convfinqa.entrypoints.api.middleware.auth import AuthMiddleware
from convfinqa.entrypoints.api.router import api_router
from convfinqa.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    register_auto_instrumentations(SETTINGS, app=app)
    container = bootstrap_application(settings=SETTINGS)
    app.state.container = container
    try:
        yield
    finally:
        await container.observability.flush()
        await container.engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="convfinqa", lifespan=lifespan)
    app.add_middleware(AuthMiddleware)
    install_exception_handlers(app)
    app.include_router(router=api_router)
    return app


def serve_app() -> None:
    uvicorn.run(
        "convfinqa.main:create_app",
        factory=True,
        host=SETTINGS.api_host,
        port=SETTINGS.api_port,
        reload=SETTINGS.api_reload,
    )
