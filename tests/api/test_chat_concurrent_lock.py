import asyncio

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.lock import SqlAlchemyConversationLock
from convfinqa.adapters.persistence.sqlalchemy.models import MessageOrm
from tests.fakes.llm import FakeLLMPort


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _create_conversation(app: FastAPI) -> str:
    async with await _client(app) as client:
        response = await client.post(
            "/v1/chat",
            headers={"X-User-Id": "alice"},
            json={"message": "hi"},
        )
        return str(response.json()["conversation_id"])


@pytest.mark.asyncio
async def test_concurrent_streams_second_returns_409_problem_with_first_finishing(
    app: FastAPI,
    fake_llm: FakeLLMPort,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    conversation_id = await _create_conversation(app)

    fake_llm.gate = asyncio.Event()
    fake_llm.stream_started = asyncio.Event()

    async def post_stream() -> tuple[int, str, dict[str, str]]:
        async with await _client(app) as client:
            response = await client.post(
                "/v1/chat/stream",
                headers={"X-User-Id": "alice"},
                json={"message": "second", "conversation_id": conversation_id},
            )
            return response.status_code, response.text, dict(response.headers)

    holding = asyncio.create_task(post_stream())
    await asyncio.wait_for(fake_llm.stream_started.wait(), timeout=2.0)

    arriving = asyncio.create_task(post_stream())
    status_b, body_b, headers_b = await asyncio.wait_for(arriving, timeout=2.0)

    assert status_b == 409
    assert headers_b["content-type"].startswith("application/problem+json")
    payload = body_b
    assert "conversation-busy" in payload
    assert conversation_id in payload

    fake_llm.gate.set()
    status_a, _body_a, _headers_a = await asyncio.wait_for(holding, timeout=2.0)
    assert status_a == 200

    async with session_factory() as session:
        result = await session.execute(
            select(MessageOrm)
            .where(MessageOrm.conversation_id == conversation_id)
            .order_by(MessageOrm.created_at)
        )
        rows = list(result.scalars().all())

    user_messages = [r for r in rows if r.role == "user"]
    user_contents = [r.content for r in user_messages]
    assert user_contents.count("second") == 2

    assistant_messages = [r for r in rows if r.role == "assistant"]
    assert len(assistant_messages) == 2


@pytest.mark.asyncio
async def test_sync_chat_concurrent_returns_409(
    app: FastAPI,
    fake_llm: FakeLLMPort,
) -> None:
    conversation_id = await _create_conversation(app)

    fake_llm.gate = asyncio.Event()
    fake_llm.stream_started = asyncio.Event()

    async def post_sync() -> tuple[int, dict[str, object]]:
        async with await _client(app) as client:
            response = await client.post(
                "/v1/chat",
                headers={"X-User-Id": "alice"},
                json={"message": "again", "conversation_id": conversation_id},
            )
            return response.status_code, response.json()

    holding = asyncio.create_task(post_sync())
    await asyncio.wait_for(fake_llm.stream_started.wait(), timeout=2.0)

    second_status, second_body = await asyncio.wait_for(post_sync(), timeout=2.0)

    assert second_status == 409
    assert second_body["status"] == 409
    assert second_body["type"] == "https://convfinqa.local/problems/conversation-busy"

    fake_llm.gate.set()
    first_status, _first_body = await asyncio.wait_for(holding, timeout=2.0)
    assert first_status == 200


@pytest.mark.asyncio
async def test_advisory_lock_serializes_then_releases_on_normal_exit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    locks = SqlAlchemyConversationLock(session_factory)
    conversation_id = "conv_lock_test_normal"

    async with locks.try_acquire(conversation_id) as outer:
        assert outer is True
        async with locks.try_acquire(conversation_id) as inner:
            assert inner is False

    async with locks.try_acquire(conversation_id) as after:
        assert after is True


@pytest.mark.asyncio
async def test_advisory_lock_releases_on_exception_simulating_worker_crash(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # AC: "simulates worker crash mid-lock and verifies next request succeeds".
    # An exception inside the with block triggers session.begin() rollback —
    # the same Postgres code path a TCP drop from a crashed backend takes
    # (pg_try_advisory_xact_lock auto-releases on transaction commit OR
    # rollback OR connection death; all three converge on the same release).
    locks = SqlAlchemyConversationLock(session_factory)
    conversation_id = "conv_lock_test_exception"

    with pytest.raises(RuntimeError, match="simulated worker crash"):
        async with locks.try_acquire(conversation_id) as acquired:
            assert acquired is True
            raise RuntimeError("simulated worker crash")

    async with locks.try_acquire(conversation_id) as recovered:
        assert recovered is True
