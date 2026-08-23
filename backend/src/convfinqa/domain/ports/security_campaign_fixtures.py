from typing import Protocol

from convfinqa.domain.entities import Document


class SecurityCampaignFixturesPort(Protocol):
    """Creates and tears down the throwaway Documents a live security
    regression campaign pins Conversations to. Kept separate from
    DocumentRepository so the campaign's write/delete needs never leak into
    the read-only path every other document consumer relies on."""

    async def upsert_document(self, document: Document) -> None: ...

    async def delete_document(self, document_id: str) -> None: ...
