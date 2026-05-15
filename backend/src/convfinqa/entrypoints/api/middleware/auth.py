from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from convfinqa.domain.ports.session import SessionVerificationError

_SKIP_PATHS = frozenset({"/healthz", "/readyz"})

_UNAUTHORIZED_BODY = {
    "type": "https://convfinqa.local/problems/unauthorized",
    "title": "Unauthorized",
    "status": status.HTTP_401_UNAUTHORIZED,
}

_PROBLEM_CONTENT_TYPE = "application/problem+json"


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        content=_UNAUTHORIZED_BODY,
        status_code=status.HTTP_401_UNAUTHORIZED,
        media_type=_PROBLEM_CONTENT_TYPE,
    )


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        container = request.app.state.container
        if container.session is None:
            return await call_next(request)

        token = request.cookies.get("access_token")
        if not token:
            return _unauthorized()

        try:
            claims = await container.session.verify_access_token(token)
        except SessionVerificationError:
            return _unauthorized()

        if claims.user_id is None:
            return _unauthorized()

        request.state.current_user_id = claims.user_id
        return await call_next(request)
