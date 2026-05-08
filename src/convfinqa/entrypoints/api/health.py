from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}