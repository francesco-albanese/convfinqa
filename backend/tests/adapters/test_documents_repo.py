import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.documents_repo import (
    SqlAlchemyDocumentsRepository,
)
from convfinqa.domain.ports.documents_port import (
    InvalidCursorError,
    ListDocumentsQuery,
)

CORPUS = (
    (
        "doc-jkhy-2009",
        "JKHY",
        2009,
        28,
        "JKHY 2009 annual report",
        "credit union systems revenue grew",
    ),
    (
        "doc-jkhy-2010",
        "JKHY",
        2010,
        30,
        "JKHY 2010 annual report",
        "credit union systems revenue grew",
    ),
    (
        "doc-aapl-2015",
        "AAPL",
        2015,
        1,
        "AAPL 2015 annual report",
        "iphone revenue rose substantially",
    ),
    (
        "doc-msft-2020",
        "MSFT",
        2020,
        5,
        "MSFT 2020 annual report",
        "azure cloud revenue surge",
    ),
    (
        "doc-tsla-2022",
        "TSLA",
        2022,
        8,
        "TSLA 2022 annual report",
        "electric vehicle deliveries climbed",
    ),
)


@pytest.fixture
async def seeded(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for doc_id, ticker, year, page, title, pre_text in CORPUS:
            await conn.execute(
                text(
                    "INSERT INTO documents "
                    "(id, ticker, year, page, title, pre_text, post_text, table_data) "
                    "VALUES (:id, :ticker, :year, :page, :title, :pre_text, '', "
                    "CAST('{}' AS jsonb))"
                ),
                {
                    "id": doc_id,
                    "ticker": ticker,
                    "year": year,
                    "page": page,
                    "title": title,
                    "pre_text": pre_text,
                },
            )


@pytest.fixture
def repo(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyDocumentsRepository:
    return SqlAlchemyDocumentsRepository(session_factory)


async def test_get_returns_full_document_payload(
    seeded: None, repo: SqlAlchemyDocumentsRepository
) -> None:
    del seeded
    got = await repo.get("doc-jkhy-2009")

    assert got is not None
    assert got.id == "doc-jkhy-2009"
    assert got.ticker == "JKHY"
    assert got.year == 2009


async def test_get_returns_none_when_missing(
    seeded: None, repo: SqlAlchemyDocumentsRepository
) -> None:
    del seeded
    assert await repo.get("does-not-exist") is None


async def test_list_full_text_search_filters_by_q(
    seeded: None, repo: SqlAlchemyDocumentsRepository
) -> None:
    del seeded
    page = await repo.list(ListDocumentsQuery(q="iphone", limit=10))

    assert [item.id for item in page.items] == ["doc-aapl-2015"]


async def test_list_year_range_filter_applies(
    seeded: None, repo: SqlAlchemyDocumentsRepository
) -> None:
    del seeded
    page = await repo.list(ListDocumentsQuery(year_min=2015, year_max=2020, limit=10))

    assert {item.id for item in page.items} == {"doc-aapl-2015", "doc-msft-2020"}


async def test_list_paginates_via_cursor_exhausting_all_rows_exactly_once(
    seeded: None, repo: SqlAlchemyDocumentsRepository
) -> None:
    del seeded
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(10):
        page = await repo.list(ListDocumentsQuery(cursor=cursor, limit=2))
        seen.extend(item.id for item in page.items)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor
    else:
        pytest.fail("pagination did not terminate")

    expected = {doc[0] for doc in CORPUS} | {"Single_TEST/2024/page_1.pdf-1"}
    assert set(seen) == expected
    assert len(seen) == len(expected)


async def test_list_malformed_cursor_raises_invalid_cursor_error(
    seeded: None, repo: SqlAlchemyDocumentsRepository
) -> None:
    del seeded
    with pytest.raises(InvalidCursorError):
        await repo.list(ListDocumentsQuery(cursor="not-a-valid-cursor!!"))


async def test_get_preserves_wire_column_order_for_integer_like_keys(
    engine: AsyncEngine, repo: SqlAlchemyDocumentsRepository
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO documents "
                "(id, ticker, year, page, title, pre_text, post_text, "
                "table_data, column_order) "
                "VALUES (:id, 'JKHY', 2009, 28, 't', '', '', "
                "CAST(:table_data AS jsonb), :column_order) "
                "ON CONFLICT (id) DO UPDATE SET "
                "column_order = EXCLUDED.column_order, "
                "table_data = EXCLUDED.table_data"
            ),
            {
                "id": "doc-jkhy-wire-order",
                "table_data": (
                    '{"2007":{"r":1},"2008":{"r":2},"Year ended June 30, 2009":{"r":3}}'
                ),
                "column_order": [
                    "Year ended June 30, 2009",
                    "2008",
                    "2007",
                ],
            },
        )

    got = await repo.get("doc-jkhy-wire-order")

    assert got is not None
    assert got.column_order == ("Year ended June 30, 2009", "2008", "2007")
