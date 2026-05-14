from convfinqa.domain.entities import DocumentListPage
from convfinqa.domain.ports.documents_port import DocumentsPort, ListDocumentsQuery


class ListDocumentsUseCase:
    def __init__(self, documents: DocumentsPort) -> None:
        self._documents = documents

    async def execute(self, query: ListDocumentsQuery) -> DocumentListPage:
        return await self._documents.list(query)
