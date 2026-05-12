from dataclasses import dataclass, field

import pytest

from convfinqa.application.use_cases.get_document import (
    DocumentNotFoundError,
    GetDocumentUseCase,
)
from convfinqa.domain.entities import Document, DocumentListPage
from convfinqa.domain.ports.documents_port import DocumentsPort, ListDocumentsQuery


@dataclass(slots=True)
class _FakeDocsPort(DocumentsPort):
    by_id: dict[str, Document] = field(default_factory=dict[str, Document])

    async def list(self, query: ListDocumentsQuery) -> DocumentListPage:
        del query
        return DocumentListPage(items=(), next_cursor=None)

    async def get(self, document_id: str) -> Document | None:
        return self.by_id.get(document_id)


def _doc(doc_id: str) -> Document:
    return Document(
        id=doc_id,
        ticker="X",
        year=2024,
        page=1,
        title="title",
        pre_text="pre",
        post_text="post",
        table_data={},
    )


@pytest.mark.asyncio
async def test_returns_document_when_present() -> None:
    target = _doc("d1")
    fake = _FakeDocsPort(by_id={"d1": target})
    use_case = GetDocumentUseCase(documents=fake)

    got = await use_case.execute("d1")

    assert got is target


@pytest.mark.asyncio
async def test_raises_when_missing() -> None:
    use_case = GetDocumentUseCase(documents=_FakeDocsPort())

    with pytest.raises(DocumentNotFoundError):
        await use_case.execute("missing")
