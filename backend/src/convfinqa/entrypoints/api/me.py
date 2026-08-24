from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from convfinqa.entrypoints.api.dependencies import CurrentUserEmail, CurrentUserId

me_router = APIRouter(prefix="/api/v1", tags=["me"])


class MeResponse(BaseModel):
    user_id: str
    email: str | None


@me_router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(
    request: Request,
    response: Response,
    user_id: CurrentUserId,
    email: CurrentUserEmail,
) -> MeResponse:
    if request.app.state.container.session is None:
        response.headers["X-Auth-Mode"] = "local"
    return MeResponse(user_id=user_id, email=email)
