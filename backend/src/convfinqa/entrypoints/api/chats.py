from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Path, status
from pydantic import BaseModel

from convfinqa.application.parts_schema import MessagePartsEnvelope
from convfinqa.domain.entities import ConversationSummary, Message
from convfinqa.entrypoints.api.dependencies import (
    CurrentUserDep,
    GetChatMessages,
    ListChats,
)

chats_router = APIRouter(prefix="/api/v1", tags=["chats"])

CONVERSATION_ID_PATTERN = r"^[A-Za-z0-9_-]+$"
CONVERSATION_ID_MAX_LENGTH = 128


class ChatDocumentResponse(BaseModel):
    id: str
    ticker: str | None
    year: int | None
    title: str | None


class ChatSummaryResponse(BaseModel):
    id: str
    document: ChatDocumentResponse
    last_message_preview: str
    last_message_at: datetime


class ChatListResponse(BaseModel):
    items: list[ChatSummaryResponse]


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    parts: MessagePartsEnvelope | None = None


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageResponse]


def _to_summary_response(summary: ConversationSummary) -> ChatSummaryResponse:
    return ChatSummaryResponse(
        id=summary.id,
        document=ChatDocumentResponse(
            id=summary.document.id,
            ticker=summary.document.ticker,
            year=summary.document.year,
            title=summary.document.title,
        ),
        last_message_preview=summary.last_message_preview,
        last_message_at=summary.last_message_at,
    )


def _to_message_response(message: Message) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        created_at=message.created_at,
        parts=(
            MessagePartsEnvelope.model_validate(message.parts)
            if message.parts is not None
            else None
        ),
    )


@chats_router.get(
    "/chats",
    response_model=ChatListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_chats(
    user_id: CurrentUserDep,
    list_use_case: ListChats,
) -> ChatListResponse:
    summaries = await list_use_case.execute(user_id)
    return ChatListResponse(items=[_to_summary_response(s) for s in summaries])


@chats_router.get(
    "/chats/{conversation_id}/messages",
    response_model=ChatMessageListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_chat_messages(
    user_id: CurrentUserDep,
    get_use_case: GetChatMessages,
    conversation_id: Annotated[
        str,
        Path(
            min_length=1,
            max_length=CONVERSATION_ID_MAX_LENGTH,
            pattern=CONVERSATION_ID_PATTERN,
        ),
    ],
) -> ChatMessageListResponse:
    messages = await get_use_case.execute(conversation_id, user_id)
    return ChatMessageListResponse(items=[_to_message_response(m) for m in messages])
