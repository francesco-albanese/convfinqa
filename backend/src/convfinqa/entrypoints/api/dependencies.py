import uuid
from typing import Annotated

from fastapi import Depends, Request

from convfinqa.application.use_cases.delete_conversation import (
    DeleteConversationUseCase,
)
from convfinqa.application.use_cases.get_chat_messages import GetChatMessagesUseCase
from convfinqa.application.use_cases.get_document import GetDocumentUseCase
from convfinqa.application.use_cases.list_chats import ListChatsUseCase
from convfinqa.application.use_cases.list_documents import ListDocumentsUseCase
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.config import Settings
from convfinqa.container import Container
from convfinqa.entrypoints.api.errors import MissingUserIdError


def get_current_user_id(request: Request) -> uuid.UUID:
    middleware_uid: uuid.UUID | None = getattr(request.state, "current_user_id", None)
    if middleware_uid is not None:
        return middleware_uid
    container: Container = request.app.state.container
    if container.session is not None:
        raise MissingUserIdError("access_token cookie is required")
    x_user_id = request.headers.get("X-User-Id", "").strip()
    if not x_user_id:
        raise MissingUserIdError("X-User-Id header is required")
    try:
        return uuid.UUID(x_user_id)
    except ValueError as exc:
        raise MissingUserIdError("X-User-Id is not a valid UUID") from exc


def current_user_id(request: Request) -> str:
    return str(get_current_user_id(request))


def current_user_email(request: Request) -> str | None:
    middleware_email: str | None = getattr(request.state, "current_user_email", None)
    if middleware_email is not None:
        return middleware_email
    container: Container = request.app.state.container
    if container.session is None:
        return request.headers.get("X-User-Email")
    return None


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_send_message(
    container: Annotated[Container, Depends(get_container)],
) -> SendMessageUseCase:
    return container.send_message


def get_settings(
    container: Annotated[Container, Depends(get_container)],
) -> Settings:
    return container.settings


def get_list_documents(
    container: Annotated[Container, Depends(get_container)],
) -> ListDocumentsUseCase:
    return container.list_documents


def get_document(
    container: Annotated[Container, Depends(get_container)],
) -> GetDocumentUseCase:
    return container.get_document


def get_list_chats(
    container: Annotated[Container, Depends(get_container)],
) -> ListChatsUseCase:
    return container.list_chats


def get_chat_messages(
    container: Annotated[Container, Depends(get_container)],
) -> GetChatMessagesUseCase:
    return container.get_chat_messages


def get_delete_conversation(
    container: Annotated[Container, Depends(get_container)],
) -> DeleteConversationUseCase:
    return container.delete_conversation


CurrentUserId = Annotated[str, Depends(current_user_id)]
CurrentUserEmail = Annotated[str | None, Depends(current_user_email)]
CurrentUserDep = Annotated[uuid.UUID, Depends(get_current_user_id)]
SendMessage = Annotated[SendMessageUseCase, Depends(get_send_message)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ListDocuments = Annotated[ListDocumentsUseCase, Depends(get_list_documents)]
GetDocument = Annotated[GetDocumentUseCase, Depends(get_document)]
ListChats = Annotated[ListChatsUseCase, Depends(get_list_chats)]
GetChatMessages = Annotated[GetChatMessagesUseCase, Depends(get_chat_messages)]
DeleteConversation = Annotated[
    DeleteConversationUseCase, Depends(get_delete_conversation)
]
