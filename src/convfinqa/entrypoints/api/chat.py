from datetime import datetime

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from src.convfinqa.application.use_cases.send_message import (
    ConversationCreated,
    ErrorEvent,
    Finish,
    MessageStarted,
    TextDelta,
)
from src.convfinqa.domain.value_objects import StopReason
from src.convfinqa.entrypoints.api.dependencies import (
    CurrentUserId,
    SendMessage,
    SettingsDep,
)
from src.convfinqa.entrypoints.api.errors import UpstreamLLMError

chat_router = APIRouter(prefix="/v1", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = None


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
    user_id: CurrentUserId,
    send_message: SendMessage,
    settings: SettingsDep,
) -> ChatResponse:
    conversation_id = ""
    message_id = ""
    parts: list[str] = []
    stop_reason = StopReason.END_TURN
    usage_payload: ChatUsage | None = None
    created_at: datetime | None = None

    async for event in send_message.stream(
        user_id=user_id,
        conversation_id=body.conversation_id,
        user_text=body.message,
    ):
        match event:
            case ConversationCreated(conversation_id=cid):
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

    assert created_at is not None
    return ChatResponse(
        id=message_id,
        conversation_id=conversation_id,
        role="assistant",
        content="".join(parts),
        model=settings.llm_model,
        stop_reason=stop_reason.value,
        usage=usage_payload,
        created_at=created_at,
    )
