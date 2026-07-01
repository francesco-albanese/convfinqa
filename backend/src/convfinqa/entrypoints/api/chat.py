from datetime import datetime
from typing import Self

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from convfinqa.application.agent.stream_events import (
    Citation,
    ConcurrentRequest,
    ConversationResolved,
    ConversationTitle,
    ErrorEvent,
    Finish,
    MessageStarted,
    ReasoningDelta,
    ReasoningEnd,
    ReasoningStart,
    TextDelta,
    ToolCallArgsComplete,
    ToolCallStart,
    ToolResult,
)
from convfinqa.config import Settings
from convfinqa.domain.value_objects import StopReason
from convfinqa.entrypoints.api.dependencies import (
    CurrentUserDep,
    SendMessage,
    SettingsDep,
)
from convfinqa.entrypoints.api.errors import ConversationBusyError, UpstreamLLMError
from convfinqa.entrypoints.api.sse import (
    UI_MESSAGE_STREAM_HEADERS,
    prepend_event,
    to_ui_message_stream,
)

chat_router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32_000)
    conversation_id: str | None = None
    document_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=512,
        pattern=r"^[A-Za-z0-9._/\-]+$",
    )
    model: str | None = None

    @model_validator(mode="after")
    def _document_id_required_for_new_conversation(self) -> Self:
        if self.conversation_id is None and self.document_id is None:
            raise ValueError("document_id is required when starting a new conversation")
        return self


def _resolve_model(requested: str | None, settings: Settings) -> str:
    if requested is not None and requested not in settings.llm_models:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="requested model is not supported",
        )
    return requested or settings.llm_model


class ChatUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class ChatResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    model: str
    stop_reason: str
    usage: ChatUsage | None
    created_at: datetime


@chat_router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def sync_chat(
    body: ChatRequest,
    user_id: CurrentUserDep,
    send_message: SendMessage,
    settings: SettingsDep,
) -> ChatResponse:
    resolved_model = _resolve_model(body.model, settings)
    conversation_id = ""
    message_id = ""
    parts: list[str] = []
    stop_reason = StopReason.END_TURN
    usage_payload: ChatUsage | None = None
    created_at: datetime | None = None

    events = send_message.stream(
        user_id=user_id,
        conversation_id=body.conversation_id,
        user_text=body.message,
        document_id=body.document_id,
        model=resolved_model,
    )
    try:
        async for event in events:
            match event:
                case ConcurrentRequest(conversation_id=cid):
                    raise ConversationBusyError(cid)
                case ConversationResolved(conversation_id=cid):
                    conversation_id = cid
                case MessageStarted(message_id=mid):
                    message_id = mid
                case TextDelta(text=text):
                    parts.append(text)
                case Finish(stop_reason=sr, usage=u, created_at=ts):
                    stop_reason = sr
                    created_at = ts
                    if u is not None:
                        usage_payload = ChatUsage(
                            input_tokens=u.input_tokens,
                            output_tokens=u.output_tokens,
                        )
                case ErrorEvent(detail=detail):
                    raise UpstreamLLMError(detail)
                case (
                    ReasoningStart()
                    | ReasoningDelta()
                    | ReasoningEnd()
                    | ToolCallStart()
                    | ToolCallArgsComplete()
                    | ToolResult()
                    | Citation()
                    | ConversationTitle()
                ):
                    pass
    finally:
        await events.aclose()

    if created_at is None:
        raise UpstreamLLMError("missing Finish event")

    return ChatResponse(
        id=message_id,
        conversation_id=conversation_id,
        role="assistant",
        content="".join(parts),
        model=resolved_model,
        stop_reason=stop_reason.value,
        usage=usage_payload,
        created_at=created_at,
    )


@chat_router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
)
async def stream_chat(
    body: ChatRequest,
    user_id: CurrentUserDep,
    send_message: SendMessage,
    settings: SettingsDep,
) -> StreamingResponse:
    resolved_model = _resolve_model(body.model, settings)
    events = send_message.stream(
        user_id=user_id,
        conversation_id=body.conversation_id,
        user_text=body.message,
        document_id=body.document_id,
        model=resolved_model,
    )
    first_event = await anext(events)

    if isinstance(first_event, ConcurrentRequest):
        await events.aclose()
        raise ConversationBusyError(first_event.conversation_id)

    return StreamingResponse(
        to_ui_message_stream(prepend_event(first_event, events)),
        media_type="text/event-stream",
        headers=UI_MESSAGE_STREAM_HEADERS,
    )
