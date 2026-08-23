from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.repository import (
    SqlAlchemyDocumentRepository,
)
from convfinqa.adapters.persistence.sqlalchemy.security_campaign_fixtures_repo import (
    SqlAlchemySecurityCampaignFixturesRepository,
)
from convfinqa.domain.entities import Document

FIXTURE_DOC = Document(
    id="security-campaign-adapter-test-doc",
    ticker="SCAT",
    year=2024,
    page=1,
    title="Adapter Test Fixture",
    pre_text="pre",
    post_text="post",
    table_data={"revenue": [1, 2]},
    column_order=("fy1", "fy2"),
)


async def test_upsert_then_delete_round_trips_through_document_repository(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    fixtures = SqlAlchemySecurityCampaignFixturesRepository(session_factory)
    documents = SqlAlchemyDocumentRepository(session_factory)

    await fixtures.upsert_document(FIXTURE_DOC)
    fetched = await documents.get(FIXTURE_DOC.id)
    assert fetched is not None
    assert fetched.title == FIXTURE_DOC.title
    assert fetched.table_data == FIXTURE_DOC.table_data

    await fixtures.delete_document(FIXTURE_DOC.id)
    assert await documents.get(FIXTURE_DOC.id) is None


async def test_upsert_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    fixtures = SqlAlchemySecurityCampaignFixturesRepository(session_factory)
    documents = SqlAlchemyDocumentRepository(session_factory)

    await fixtures.upsert_document(FIXTURE_DOC)
    updated = Document(
        id=FIXTURE_DOC.id,
        ticker=FIXTURE_DOC.ticker,
        year=FIXTURE_DOC.year,
        page=FIXTURE_DOC.page,
        title="Updated title",
        pre_text=FIXTURE_DOC.pre_text,
        post_text=FIXTURE_DOC.post_text,
        table_data=FIXTURE_DOC.table_data,
        column_order=FIXTURE_DOC.column_order,
    )
    await fixtures.upsert_document(updated)

    fetched = await documents.get(FIXTURE_DOC.id)
    assert fetched is not None
    assert fetched.title == "Updated title"

    await fixtures.delete_document(FIXTURE_DOC.id)
