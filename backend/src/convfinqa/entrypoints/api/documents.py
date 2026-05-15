from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status
from pydantic import BaseModel

from convfinqa.domain.entities import Document, DocumentListPage
from convfinqa.domain.ports.documents_port import ListDocumentsQuery
from convfinqa.entrypoints.api.dependencies import GetDocument, ListDocuments

documents_router = APIRouter(prefix="/api/v1", tags=["documents"])

DOCUMENT_ID_PATTERN = r"^[A-Za-z0-9._/\-]+$"
DOCUMENT_ID_MAX_LENGTH = 512


class DocumentSummaryResponse(BaseModel):
    id: str
    ticker: str | None
    year: int | None
    page: int | None
    title: str | None


class DocumentListResponse(BaseModel):
    items: list[DocumentSummaryResponse]
    next_cursor: str | None


class DocumentResponse(BaseModel):
    id: str
    ticker: str | None
    year: int | None
    page: int | None
    title: str | None
    pre_text: str | None
    post_text: str | None
    table_data: dict[str, Any] | None
    column_order: list[str] | None


def _to_list_response(page: DocumentListPage) -> DocumentListResponse:
    return DocumentListResponse(
        items=[
            DocumentSummaryResponse(
                id=item.id,
                ticker=item.ticker,
                year=item.year,
                page=item.page,
                title=item.title,
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


def _to_document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        ticker=document.ticker,
        year=document.year,
        page=document.page,
        title=document.title,
        pre_text=document.pre_text,
        post_text=document.post_text,
        table_data=document.table_data,
        column_order=(
            list(document.column_order) if document.column_order is not None else None
        ),
    )


@documents_router.get(
    "/documents",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_documents(
    list_use_case: ListDocuments,
    q: Annotated[str | None, Query(max_length=500)] = None,
    year_min: Annotated[int | None, Query(ge=1900, le=2200)] = None,
    year_max: Annotated[int | None, Query(ge=1900, le=2200)] = None,
    cursor: Annotated[str | None, Query(max_length=1024)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> DocumentListResponse:
    page = await list_use_case.execute(
        ListDocumentsQuery(
            q=q,
            year_min=year_min,
            year_max=year_max,
            cursor=cursor,
            limit=limit,
        )
    )
    return _to_list_response(page)


@documents_router.get(
    "/documents/{document_id:path}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_document(
    get_use_case: GetDocument,
    document_id: Annotated[
        str,
        Path(
            min_length=1,
            max_length=DOCUMENT_ID_MAX_LENGTH,
            pattern=DOCUMENT_ID_PATTERN,
        ),
    ],
) -> DocumentResponse:
    document = await get_use_case.execute(document_id)
    return _to_document_response(document)
