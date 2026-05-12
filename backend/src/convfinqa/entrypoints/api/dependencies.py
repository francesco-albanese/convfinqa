from typing import Annotated

from fastapi import Depends, Header, Request

from convfinqa.application.use_cases.get_document import GetDocumentUseCase
from convfinqa.application.use_cases.list_documents import ListDocumentsUseCase
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.config import Settings
from convfinqa.container import Container
from convfinqa.entrypoints.api.errors import MissingUserIdError


def current_user_id(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> str:
    if not x_user_id or not x_user_id.strip():
        raise MissingUserIdError("X-User-Id header is required")
    return x_user_id


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


CurrentUserId = Annotated[str, Depends(current_user_id)]
SendMessage = Annotated[SendMessageUseCase, Depends(get_send_message)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
ListDocuments = Annotated[ListDocumentsUseCase, Depends(get_list_documents)]
GetDocument = Annotated[GetDocumentUseCase, Depends(get_document)]
