from fastapi import APIRouter

from convfinqa.entrypoints.api.chat import chat_router
from convfinqa.entrypoints.api.chats import chats_router
from convfinqa.entrypoints.api.documents import documents_router
from convfinqa.entrypoints.api.health import router as health_router_inner
from convfinqa.entrypoints.api.me import me_router

api_router = APIRouter()
api_router.include_router(router=health_router_inner)
api_router.include_router(router=me_router)
api_router.include_router(router=chat_router)
api_router.include_router(router=chats_router)
api_router.include_router(router=documents_router)
