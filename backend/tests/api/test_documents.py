import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

CORPUS: tuple[tuple[str, str, int, int, str, str], ...] = (
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


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture(loop_scope="session")
async def empty_documents(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM documents"))


@pytest_asyncio.fixture(loop_scope="session")
async def seeded_corpus(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM documents"))
        for doc_id, ticker, year, page, title, pre_text in CORPUS:
            await conn.execute(
                text(
                    "INSERT INTO documents "
                    "(id, ticker, year, page, title, pre_text, post_text, "
                    "table_data) "
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


@pytest.mark.asyncio
async def test_list_documents_empty_db_returns_empty_page(
    app: FastAPI, empty_documents: None
) -> None:
    del empty_documents
    async with await _client(app) as client:
        response = await client.get("/v1/documents")

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


@pytest.mark.asyncio
async def test_list_documents_search_returns_matching_rows(
    app: FastAPI, seeded_corpus: None
) -> None:
    del seeded_corpus
    async with await _client(app) as client:
        response = await client.get("/v1/documents", params={"q": "jkhy"})

    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert ids == {"doc-jkhy-2009", "doc-jkhy-2010"}


@pytest.mark.asyncio
async def test_list_documents_pagination_exhausts_corpus_exactly_once(
    app: FastAPI, seeded_corpus: None
) -> None:
    del seeded_corpus
    seen: list[str] = []
    cursor: str | None = None

    async with await _client(app) as client:
        for _ in range(10):
            params: dict[str, str] = {"limit": "2"}
            if cursor is not None:
                params["cursor"] = cursor
            response = await client.get("/v1/documents", params=params)
            assert response.status_code == 200
            body = response.json()
            seen.extend(item["id"] for item in body["items"])
            if body["next_cursor"] is None:
                break
            cursor = body["next_cursor"]
        else:
            pytest.fail("pagination did not terminate")

    expected = {doc[0] for doc in CORPUS}
    assert set(seen) == expected
    assert len(seen) == len(expected)


@pytest.mark.asyncio
async def test_get_document_unknown_id_returns_404_problem(
    app: FastAPI, seeded_corpus: None
) -> None:
    del seeded_corpus
    async with await _client(app) as client:
        response = await client.get("/v1/documents/doc-does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 404


@pytest.mark.asyncio
async def test_get_document_returns_full_payload_for_slash_bearing_id(
    app: FastAPI, seeded_document_id: str
) -> None:
    async with await _client(app) as client:
        response = await client.get(f"/v1/documents/{seeded_document_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == seeded_document_id
    assert body["ticker"] == "TEST"
    assert body["year"] == 2024
    assert body["pre_text"] == "fixture pre-text"
    assert body["table_data"] == {"revenue": [100, 200]}


@pytest.mark.asyncio
async def test_list_documents_malformed_cursor_returns_400_problem(
    app: FastAPI, seeded_corpus: None
) -> None:
    del seeded_corpus
    async with await _client(app) as client:
        response = await client.get(
            "/v1/documents", params={"cursor": "not-a-valid-cursor!!"}
        )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 400
