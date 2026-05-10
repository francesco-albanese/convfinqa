import logging
import uuid
from typing import cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from convfinqa.application.use_cases.send_message import (
    ConversationNotFoundError,
)
from convfinqa.logging import get_logger

PROBLEM_BASE = "https://convfinqa.local/problems"
PROBLEM_CONTENT_TYPE = "application/problem+json"

logger = get_logger("convfinqa.errors")


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str | None = None


def _problem_response(problem: Problem) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_CONTENT_TYPE,
    )


def _request_id(request: Request) -> str:
    rid = request.headers.get("x-request-id")
    if rid:
        return rid
    return uuid.uuid4().hex


class MissingUserIdError(Exception):
    pass


class UpstreamLLMError(Exception):
    pass


class ConversationBusyError(Exception):
    def __init__(self, conversation_id: str) -> None:
        super().__init__(conversation_id)
        self.conversation_id = conversation_id


def _log(
    *,
    level: int,
    request: Request,
    exc: Exception,
    status_code: int,
    user_id: str | None,
) -> None:
    logger.log(
        level,
        "request_failed",
        extra={
            "exc_type": exc.__class__.__name__,
            "exc_message": str(exc) or exc.__class__.__name__,
            "route": request.url.path,
            "method": request.method,
            "status": status_code,
            "request_id": _request_id(request),
            "user_id": user_id,
        },
    )


async def _handle_missing_user_id(request: Request, exc: Exception) -> JSONResponse:
    problem = Problem(
        type=f"{PROBLEM_BASE}/missing-user-id",
        title="Missing X-User-Id header",
        status=status.HTTP_401_UNAUTHORIZED,
        detail="X-User-Id header is required.",
    )
    _log(
        level=logging.INFO,
        request=request,
        exc=exc,
        status_code=problem.status,
        user_id=None,
    )
    return _problem_response(problem)


async def _handle_conversation_not_found(
    request: Request, exc: Exception
) -> JSONResponse:
    problem = Problem(
        type=f"{PROBLEM_BASE}/conversation-not-found",
        title="Conversation not found",
        status=status.HTTP_404_NOT_FOUND,
        detail="No conversation with that id exists for this user.",
    )
    _log(
        level=logging.INFO,
        request=request,
        exc=exc,
        status_code=problem.status,
        user_id=request.headers.get("x-user-id"),
    )
    return _problem_response(problem)


async def _handle_validation(request: Request, exc: Exception) -> JSONResponse:
    validation_exc = cast(RequestValidationError, exc)
    problem = Problem(
        type=f"{PROBLEM_BASE}/validation-error",
        title="Request validation failed",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(validation_exc.errors()),
    )
    _log(
        level=logging.INFO,
        request=request,
        exc=exc,
        status_code=problem.status,
        user_id=request.headers.get("x-user-id"),
    )
    return _problem_response(problem)


async def _handle_upstream(request: Request, exc: Exception) -> JSONResponse:
    problem = Problem(
        type=f"{PROBLEM_BASE}/upstream-error",
        title="Upstream LLM error",
        status=status.HTTP_502_BAD_GATEWAY,
        detail=str(exc) or exc.__class__.__name__,
    )
    _log(
        level=logging.WARNING,
        request=request,
        exc=exc,
        status_code=problem.status,
        user_id=request.headers.get("x-user-id"),
    )
    return _problem_response(problem)


async def _handle_conversation_busy(request: Request, exc: Exception) -> JSONResponse:
    busy_exc = cast(ConversationBusyError, exc)
    problem = Problem(
        type=f"{PROBLEM_BASE}/conversation-busy",
        title="Conversation busy",
        status=status.HTTP_409_CONFLICT,
        detail=(
            f"Another request is already in flight for conversation "
            f"{busy_exc.conversation_id}."
        ),
    )
    _log(
        level=logging.INFO,
        request=request,
        exc=exc,
        status_code=problem.status,
        user_id=request.headers.get("x-user-id"),
    )
    return _problem_response(problem)


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    problem = Problem(
        type=f"{PROBLEM_BASE}/internal-server-error",
        title="Internal server error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred.",
    )
    _log(
        level=logging.ERROR,
        request=request,
        exc=exc,
        status_code=problem.status,
        user_id=request.headers.get("x-user-id"),
    )
    return _problem_response(problem)


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(MissingUserIdError, _handle_missing_user_id)
    app.add_exception_handler(ConversationNotFoundError, _handle_conversation_not_found)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(UpstreamLLMError, _handle_upstream)
    app.add_exception_handler(ConversationBusyError, _handle_conversation_busy)
    app.add_exception_handler(Exception, _handle_unexpected)
