from convfinqa.domain.entities import Document
from convfinqa.domain.ports.documents_port import DocumentsPort


class DocumentNotFoundError(Exception):
    pass


class GetDocumentUseCase:
    def __init__(self, documents: DocumentsPort) -> None:
        self._documents = documents

    async def execute(self, document_id: str) -> Document:
        document = await self._documents.get(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document
