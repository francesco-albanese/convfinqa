from fastapi import APIRouter

from src.convfinqa.entrypoints.api.chat import chat_router
from src.convfinqa.entrypoints.api.health import router as health_router_inner

api_router = APIRouter()
api_router.include_router(router=health_router_inner)
api_router.include_router(router=chat_router)
