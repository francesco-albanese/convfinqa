from fastapi import APIRouter

from .health import router

health_router = APIRouter(prefix="/api")
health_router.include_router(router=router)