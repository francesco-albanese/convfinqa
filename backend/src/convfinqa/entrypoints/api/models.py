from fastapi import APIRouter, status
from pydantic import BaseModel

from convfinqa.entrypoints.api.dependencies import SettingsDep

models_router = APIRouter(prefix="/api/v1", tags=["models"])


class ModelsResponse(BaseModel):
    models: list[str]
    default: str


@models_router.get(
    "/models",
    response_model=ModelsResponse,
    status_code=status.HTTP_200_OK,
)
async def list_models(settings: SettingsDep) -> ModelsResponse:
    return ModelsResponse(models=settings.llm_models, default=settings.llm_model)
