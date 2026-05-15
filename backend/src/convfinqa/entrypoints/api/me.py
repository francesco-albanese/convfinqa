from fastapi import APIRouter, status
from pydantic import BaseModel

from convfinqa.entrypoints.api.dependencies import CurrentUserEmail, CurrentUserId

me_router = APIRouter(prefix="/api/v1", tags=["me"])


class MeResponse(BaseModel):
    user_id: str
    email: str | None


@me_router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(
    user_id: CurrentUserId,
    email: CurrentUserEmail,
) -> MeResponse:
    return MeResponse(user_id=user_id, email=email)
