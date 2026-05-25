from dataclasses import dataclass, field

import pytest

from convfinqa.application.use_cases.list_documents import ListDocumentsUseCase
from convfinqa.domain.entities import Document, DocumentListPage, DocumentSummary
from convfinqa.domain.ports.documents_port import DocumentsPort, ListDocumentsQuery


@dataclass(slots=True)
class _FakeDocsPort(DocumentsPort):
    next_page: DocumentListPage = field(
        default_factory=lambda: DocumentListPage(items=(), next_cursor=None)
    )
    seen: list[ListDocumentsQuery] = field(default_factory=list[ListDocumentsQuery])

    async def list(self, query: ListDocumentsQuery) -> DocumentListPage:
        self.seen.append(query)
        return self.next_page

    async def get(self, document_id: str) -> Document | None:
        del document_id
        return None


@pytest.mark.asyncio
async def test_use_case_passes_query_arguments_through_to_port() -> None:
    fake = _FakeDocsPort()
    use_case = ListDocumentsUseCase(documents=fake)

    await use_case.execute(
        ListDocumentsQuery(
            q="jkhy", year_min=2009, year_max=2012, cursor="abc", limit=25
        )
    )

    assert fake.seen == [
        ListDocumentsQuery(
            q="jkhy", year_min=2009, year_max=2012, cursor="abc", limit=25
        )
    ]


@pytest.mark.asyncio
async def test_use_case_returns_page_returned_by_port() -> None:
    page = DocumentListPage(
        items=(DocumentSummary(id="x", ticker="X", year=2020, page=1, title="X 2020"),),
        next_cursor="next-cursor-token",
    )
    fake = _FakeDocsPort(next_page=page)
    use_case = ListDocumentsUseCase(documents=fake)

    got = await use_case.execute(ListDocumentsQuery())

    assert got is page
