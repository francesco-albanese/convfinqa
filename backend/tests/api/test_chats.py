from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

DOC_AAA = "doc-aaa-2024"
DOC_BBB = "doc-bbb-2025"

CONV_ALICE_AAA_OLD = "conv-alice-aaa-old"
CONV_ALICE_BBB_NEW = "conv-alice-bbb-new"
CONV_BOB_AAA = "conv-bob-aaa"

ALICE_UUID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
BOB_UUID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


async def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _seed_documents(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for doc_id, ticker, year, title in (
            (DOC_AAA, "AAA", 2024, "AAA 2024 annual report"),
            (DOC_BBB, "BBB", 2025, "BBB 2025 annual report"),
        ):
            await conn.execute(
                text(
                    "INSERT INTO documents "
                    "(id, ticker, year, page, title, pre_text, post_text, "
                    "table_data) "
                    "VALUES (:id, :ticker, :year, 1, :title, '', '', "
                    "CAST('{}' AS jsonb))"
                ),
                {"id": doc_id, "ticker": ticker, "year": year, "title": title},
            )


async def _seed_users(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for user_uuid, cognito_sub, email in (
            (ALICE_UUID, "sub-alice-chats", "alice@example.com"),
            (BOB_UUID, "sub-bob-chats", "bob@example.com"),
        ):
            await conn.execute(
                text(
                    "INSERT INTO users (id, cognito_sub, email) "
                    "VALUES (CAST(:id AS uuid), :sub, :email) "
                    "ON CONFLICT (cognito_sub) DO NOTHING"
                ),
                {"id": user_uuid, "sub": cognito_sub, "email": email},
            )


async def _insert_conversation(
    engine: AsyncEngine,
    conv_id: str,
    user_uuid: str,
    document_id: str,
    created_at: datetime,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO conversations (id, user_id, document_id, created_at) "
                "VALUES (:id, CAST(:user_id AS uuid), :document_id, :created_at)"
            ),
            {
                "id": conv_id,
                "user_id": user_uuid,
                "document_id": document_id,
                "created_at": created_at,
            },
        )


async def _insert_message(
    engine: AsyncEngine,
    msg_id: str,
    conv_id: str,
    role: str,
    content: str,
    created_at: datetime,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO messages "
                "(id, conversation_id, role, content, created_at) "
                "VALUES (:id, :conv_id, :role, :content, :created_at)"
            ),
            {
                "id": msg_id,
                "conv_id": conv_id,
                "role": role,
                "content": content,
                "created_at": created_at,
            },
        )


@pytest_asyncio.fixture(loop_scope="session")
async def two_users_three_chats(engine: AsyncEngine) -> None:
    await _seed_users(engine)
    await _seed_documents(engine)
    base = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)

    await _insert_conversation(engine, CONV_ALICE_AAA_OLD, ALICE_UUID, DOC_AAA, base)
    await _insert_conversation(
        engine, CONV_ALICE_BBB_NEW, ALICE_UUID, DOC_BBB, base + timedelta(minutes=1)
    )
    await _insert_conversation(engine, CONV_BOB_AAA, BOB_UUID, DOC_AAA, base)

    await _insert_message(
        engine,
        "m-alice-old-1",
        CONV_ALICE_AAA_OLD,
        "user",
        "alice on AAA",
        base + timedelta(minutes=2),
    )
    await _insert_message(
        engine,
        "m-alice-old-2",
        CONV_ALICE_AAA_OLD,
        "assistant",
        "ack AAA",
        base + timedelta(minutes=3),
    )

    await _insert_message(
        engine,
        "m-alice-new-1",
        CONV_ALICE_BBB_NEW,
        "user",
        "alice on BBB",
        base + timedelta(minutes=10),
    )

    await _insert_message(
        engine,
        "m-bob-1",
        CONV_BOB_AAA,
        "user",
        "bob on AAA",
        base + timedelta(minutes=5),
    )


@pytest.mark.asyncio
async def test_list_chats_missing_user_id_header_returns_401(app: FastAPI) -> None:
    async with await _client(app) as client:
        response = await client.get("/api/v1/chats")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_chats_returns_only_requesting_users_conversations(
    app: FastAPI, two_users_three_chats: None
) -> None:
    del two_users_three_chats
    async with await _client(app) as client:
        alice_resp = await client.get(
            "/api/v1/chats", headers={"X-User-Id": ALICE_UUID}
        )
        bob_resp = await client.get("/api/v1/chats", headers={"X-User-Id": BOB_UUID})

    assert alice_resp.status_code == 200
    assert bob_resp.status_code == 200

    alice_ids = [item["id"] for item in alice_resp.json()["items"]]
    bob_ids = [item["id"] for item in bob_resp.json()["items"]]

    assert set(alice_ids) == {CONV_ALICE_AAA_OLD, CONV_ALICE_BBB_NEW}
    assert set(bob_ids) == {CONV_BOB_AAA}


@pytest.mark.asyncio
async def test_list_chats_orders_by_last_message_at_desc_and_groups_by_document(
    app: FastAPI, two_users_three_chats: None
) -> None:
    del two_users_three_chats
    async with await _client(app) as client:
        response = await client.get("/api/v1/chats", headers={"X-User-Id": ALICE_UUID})

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["id"] for item in items] == [
        CONV_ALICE_BBB_NEW,
        CONV_ALICE_AAA_OLD,
    ]

    by_document: dict[str, list[str]] = {}
    for item in items:
        by_document.setdefault(item["document"]["id"], []).append(item["id"])
    assert by_document == {
        DOC_BBB: [CONV_ALICE_BBB_NEW],
        DOC_AAA: [CONV_ALICE_AAA_OLD],
    }


@pytest.mark.asyncio
async def test_list_chats_document_shape_omits_page_and_includes_title(
    app: FastAPI, two_users_three_chats: None
) -> None:
    del two_users_three_chats
    async with await _client(app) as client:
        response = await client.get("/api/v1/chats", headers={"X-User-Id": ALICE_UUID})

    document = response.json()["items"][0]["document"]
    assert set(document.keys()) == {"id", "ticker", "year", "title"}


@pytest.mark.asyncio
async def test_get_chat_messages_returns_messages_in_order(
    app: FastAPI, two_users_three_chats: None
) -> None:
    del two_users_three_chats
    async with await _client(app) as client:
        response = await client.get(
            f"/api/v1/chats/{CONV_ALICE_AAA_OLD}/messages",
            headers={"X-User-Id": ALICE_UUID},
        )

    assert response.status_code == 200
    items = response.json()["items"]
    assert [m["role"] for m in items] == ["user", "assistant"]
    assert [m["content"] for m in items] == ["alice on AAA", "ack AAA"]


@pytest.mark.asyncio
async def test_get_chat_messages_cross_user_access_returns_404(
    app: FastAPI, two_users_three_chats: None
) -> None:
    del two_users_three_chats
    async with await _client(app) as client:
        response = await client.get(
            f"/api/v1/chats/{CONV_ALICE_AAA_OLD}/messages",
            headers={"X-User-Id": BOB_UUID},
        )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 404


@pytest.mark.asyncio
async def test_get_chat_messages_unknown_conversation_returns_404(
    app: FastAPI,
) -> None:
    async with await _client(app) as client:
        response = await client.get(
            "/api/v1/chats/conv_deadbeefdeadbeefdeadbeefdeadbeef/messages",
            headers={"X-User-Id": ALICE_UUID},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_chat_messages_missing_user_id_header_returns_401(
    app: FastAPI,
) -> None:
    async with await _client(app) as client:
        response = await client.get(
            "/api/v1/chats/conv_deadbeefdeadbeefdeadbeefdeadbeef/messages"
        )

    assert response.status_code == 401
