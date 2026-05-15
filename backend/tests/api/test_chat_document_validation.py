import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.models import ConversationOrm
from tests.conftest import SEEDED_USER_UUID
from tests.fakes.llm import FakeLLMPort


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_new_conversation_without_document_id_returns_422(app: FastAPI) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={"message": "hi"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == 422
    assert "document_id" in body["detail"]


@pytest.mark.asyncio
async def test_new_conversation_with_unknown_document_id_returns_404(
    app: FastAPI,
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={"message": "hi", "document_id": "nope"},
        )

    assert response.status_code == 404
    body = response.json()
    assert body["status"] == 404
    assert "document" in body["title"].lower()


@pytest.mark.asyncio
async def test_existing_conversation_resumes_using_stored_document_id(
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
    fake_llm: FakeLLMPort,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        first = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={"message": "first", "document_id": seeded_document_id},
        )
        conversation_id = first.json()["conversation_id"]

        second = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={"message": "second", "conversation_id": conversation_id},
        )

    assert second.status_code == 200

    async with session_factory() as session:
        result = await session.execute(
            select(ConversationOrm).where(ConversationOrm.id == conversation_id)
        )
        conv = result.scalar_one()

    assert conv.document_id == seeded_document_id
    assert "TEST 2024 annual report" in fake_llm.seen_systems[0]
    assert fake_llm.seen_systems[0] == fake_llm.seen_systems[1]


@pytest.mark.asyncio
async def test_stream_new_conversation_with_document_id_streams_successfully(
    app: FastAPI,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat/stream",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={"message": "hi", "document_id": seeded_document_id},
        )

    assert response.status_code == 200
    assert "data-conversation" in response.text
    assert "[DONE]" in response.text
