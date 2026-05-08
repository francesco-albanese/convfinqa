from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from .config import Settings
from .container import Container
from .entrypoints.api.router import health_router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Implemented a lifespan so we can tear down
    the database later
    """
    settings = Settings()
    app.state.container = Container.bootstrap_application(settings=settings)
    yield
    # teardown DB later

def create_app() -> FastAPI:
    app = FastAPI(title="convfinqa", lifespan=lifespan)
    app.include_router(router=health_router)
    return app
