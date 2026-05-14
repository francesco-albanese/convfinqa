from dataclasses import dataclass
from typing import Protocol

from convfinqa.domain.entities import Document, DocumentListPage


@dataclass(frozen=True, slots=True)
class ListDocumentsQuery:
    q: str | None = None
    year_min: int | None = None
    year_max: int | None = None
    cursor: str | None = None
    limit: int = 50


class InvalidCursorError(Exception):
    pass


class DocumentsPort(Protocol):
    async def list(self, query: ListDocumentsQuery) -> DocumentListPage: ...

    async def get(self, document_id: str) -> Document | None: ...
