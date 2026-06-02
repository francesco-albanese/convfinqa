import logging

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from convfinqa.domain.ports.session import SessionVerificationError
from convfinqa.logging import get_logger

logger = get_logger("convfinqa.auth")

_SKIP_PATHS = frozenset({"/healthz", "/readyz"})
# /docs, /openapi.json, /redoc are intentionally NOT in _SKIP_PATHS:
# API discovery is restricted to authenticated callers in production.

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
        if request.scope["path"] in _SKIP_PATHS:
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
        except Exception as exc:
            logger.log(
                logging.WARNING,
                "auth_verification_failed",
                extra={
                    "exc_type": exc.__class__.__name__,
                    "exc_message": str(exc) or exc.__class__.__name__,
                    "route": request.url.path,
                    "method": request.method,
                    "status": status.HTTP_401_UNAUTHORIZED,
                },
            )
            return _unauthorized()

        if claims.user_id is None:
            return _unauthorized()

        request.state.current_user_id = claims.user_id
        request.state.current_user_email = claims.email
        return await call_next(request)
