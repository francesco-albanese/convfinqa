import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.models import MessageOrm
from tests.conftest import SEEDED_USER_UUID
from tests.fakes.llm import FakeLLMPort

MALLORY_UUID = "ffffffff-ffff-ffff-ffff-ffffffffffff"


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _messages_for(
    session_factory: async_sessionmaker[AsyncSession], conversation_id: str
) -> list[MessageOrm]:
    async with session_factory() as session:
        result = await session.execute(
            select(MessageOrm)
            .where(MessageOrm.conversation_id == conversation_id)
            .order_by(MessageOrm.created_at)
        )
        return list(result.scalars().all())


@pytest.mark.asyncio
async def test_sync_chat_happy_path_creates_conversation_and_persists_messages(
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={
                "message": "hi, about the document",
                "document_id": seeded_document_id,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert body["content"] == "Hello world"
    assert body["stop_reason"] == "end_turn"
    assert body["conversation_id"].startswith("conv_")
    assert body["id"].startswith("msg_")
    assert body["usage"] == {"input_tokens": 12, "output_tokens": 2}

    rows = await _messages_for(session_factory, body["conversation_id"])
    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[0].content == "hi, about the document"
    assert rows[1].content == "Hello world"
    assert rows[1].stop_reason == "end_turn"


@pytest.mark.asyncio
async def test_sync_chat_forwards_default_model_when_omitted(
    app: FastAPI,
    fake_llm: FakeLLMPort,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={
                "message": "hi, about the document",
                "document_id": seeded_document_id,
            },
        )

    assert response.status_code == 200
    default_model = "bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert response.json()["model"] == default_model
    assert fake_llm.seen_models == [default_model]


@pytest.mark.asyncio
async def test_sync_chat_forwards_chosen_model_when_in_allowlist(
    app: FastAPI,
    fake_llm: FakeLLMPort,
    seeded_document_id: str,
) -> None:
    chosen_model = "gemini/gemini-3.5-flash"
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={
                "message": "hi, about the document",
                "document_id": seeded_document_id,
                "model": chosen_model,
            },
        )

    assert response.status_code == 200
    assert response.json()["model"] == chosen_model
    assert fake_llm.seen_models == [chosen_model]


@pytest.mark.asyncio
async def test_sync_chat_rejects_model_outside_allowlist_with_422(
    app: FastAPI,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={
                "message": "hi",
                "document_id": seeded_document_id,
                "model": "openai/gpt-not-allowed",
            },
        )

    assert response.status_code == 422
    assert "not supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sync_chat_continuation_includes_prior_history(
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
    fake_llm: FakeLLMPort,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        first = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={
                "message": "first, about the document",
                "document_id": seeded_document_id,
            },
        )
        conversation_id = first.json()["conversation_id"]

        second = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={
                "message": "second, about the document",
                "conversation_id": conversation_id,
            },
        )

    assert second.status_code == 200
    rows = await _messages_for(session_factory, conversation_id)
    assert [r.role for r in rows] == ["user", "assistant", "user", "assistant"]

    second_call_messages = fake_llm.seen_messages[1]
    contents: list[object] = [
        m["content"] for m in second_call_messages if isinstance(m, dict)
    ]
    assert "first, about the document" in contents
    assert "Hello world" in contents
    assert contents[-1] == "second, about the document"


@pytest.mark.asyncio
async def test_sync_chat_cross_tenant_returns_404_problem(
    app: FastAPI,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        owned = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={"message": "hi", "document_id": seeded_document_id},
        )
        conversation_id = owned.json()["conversation_id"]

        intruder = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": MALLORY_UUID},
            json={"message": "leak", "conversation_id": conversation_id},
        )

    assert intruder.status_code == 404
    assert intruder.headers["content-type"].startswith("application/problem+json")
    assert intruder.json()["status"] == 404


@pytest.mark.asyncio
async def test_sync_chat_missing_user_id_returns_401_problem(
    app: FastAPI,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            json={"message": "hi", "document_id": seeded_document_id},
        )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 401


@pytest.mark.asyncio
async def test_sync_chat_empty_message_returns_422(
    app: FastAPI,
    seeded_document_id: str,
) -> None:
    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={"message": "", "document_id": seeded_document_id},
        )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 422
    detail = body["detail"]
    assert "input" not in detail
    assert "pydantic.dev" not in detail


@pytest.mark.asyncio
async def test_sync_chat_llm_error_returns_502_and_persists_partial(
    app: FastAPI,
    session_factory: async_sessionmaker[AsyncSession],
    fake_llm: FakeLLMPort,
    seeded_document_id: str,
) -> None:
    fake_llm.deltas = ("partial ", "more")
    fake_llm.raise_after = 1
    fake_llm.raise_with = RuntimeError("bedrock said no")

    async with await _client(app) as client:
        response = await client.post(
            "/api/v1/chat",
            headers={"X-User-Id": SEEDED_USER_UUID},
            json={
                "message": "hi, about the document",
                "document_id": seeded_document_id,
            },
        )

    assert response.status_code == 502
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 502
    detail = body.get("detail") or ""
    assert "bedrock said no" not in detail
    assert detail == "The upstream LLM provider returned an error."

    convs = fake_llm.seen_systems
    assert len(convs) == 1

    async with session_factory() as session:
        result = await session.execute(
            select(MessageOrm).order_by(MessageOrm.created_at)
        )
        rows = list(result.scalars().all())

    assert [r.role for r in rows] == ["user", "assistant"]
    assert rows[0].content == "hi, about the document"
    assert rows[1].content == "partial "
    assert rows[1].stop_reason == "interrupted"
