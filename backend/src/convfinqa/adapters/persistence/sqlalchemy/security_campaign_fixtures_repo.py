from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.models import DocumentOrm
from convfinqa.domain.entities import Document


class SqlAlchemySecurityCampaignFixturesRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_document(self, document: Document) -> None:
        async with self._session_factory() as session:
            await session.merge(
                DocumentOrm(
                    id=document.id,
                    ticker=document.ticker,
                    year=document.year,
                    page=document.page,
                    title=document.title,
                    pre_text=document.pre_text,
                    post_text=document.post_text,
                    table_data=document.table_data,
                    column_order=(
                        list(document.column_order)
                        if document.column_order is not None
                        else None
                    ),
                    conv_questions=(
                        list(document.conv_questions)
                        if document.conv_questions is not None
                        else None
                    ),
                )
            )
            await session.commit()

    async def delete_document(self, document_id: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                delete(DocumentOrm).where(DocumentOrm.id == document_id)
            )
            await session.commit()
