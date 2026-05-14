from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.persistence.sqlalchemy.repository import (
    LAST_MESSAGE_PREVIEW_MAX_CHARS,
    SqlAlchemyConversationRepository,
)
from convfinqa.domain.value_objects import Role

DOC_AAA = "doc-aaa-2024"
DOC_BBB = "doc-bbb-2025"
DOC_CCC = "doc-ccc-2026"


async def _seed_documents(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for doc_id, ticker, year in (
            (DOC_AAA, "AAA", 2024),
            (DOC_BBB, "BBB", 2025),
            (DOC_CCC, "CCC", 2026),
        ):
            await conn.execute(
                text(
                    "INSERT INTO documents "
                    "(id, ticker, year, page, title, pre_text, post_text, table_data) "
                    "VALUES (:id, :ticker, :year, 1, :title, '', '', "
                    "CAST('{}' AS jsonb))"
                ),
                {
                    "id": doc_id,
                    "ticker": ticker,
                    "year": year,
                    "title": f"{ticker} {year}",
                },
            )


async def _insert_conversation(
    engine: AsyncEngine,
    conv_id: str,
    user_id: str,
    document_id: str,
    created_at: datetime,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO conversations (id, user_id, document_id, created_at) "
                "VALUES (:id, :user_id, :document_id, :created_at)"
            ),
            {
                "id": conv_id,
                "user_id": user_id,
                "document_id": document_id,
                "created_at": created_at,
            },
        )


async def _insert_message(
    engine: AsyncEngine,
    msg_id: str,
    conv_id: str,
    role: Role,
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
                "role": role.value,
                "content": content,
                "created_at": created_at,
            },
        )


@pytest.fixture
def repo(
    session_factory: async_sessionmaker[AsyncSession],
) -> SqlAlchemyConversationRepository:
    return SqlAlchemyConversationRepository(session_factory)


async def test_list_for_user_returns_conversations_sorted_by_last_message_at_desc(
    engine: AsyncEngine, repo: SqlAlchemyConversationRepository
) -> None:
    await _seed_documents(engine)
    base = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    await _insert_conversation(engine, "conv-1", "alice", DOC_AAA, base)
    await _insert_conversation(engine, "conv-2", "alice", DOC_BBB, base)
    await _insert_message(
        engine,
        "m-1",
        "conv-1",
        Role.USER,
        "first chat msg",
        base + timedelta(minutes=1),
    )
    await _insert_message(
        engine,
        "m-2",
        "conv-2",
        Role.USER,
        "second chat msg",
        base + timedelta(minutes=10),
    )

    summaries = await repo.list_for_user("alice")

    assert [s.id for s in summaries] == ["conv-2", "conv-1"]
    assert summaries[0].document.ticker == "BBB"
    assert summaries[1].document.ticker == "AAA"


async def test_list_for_user_preview_is_latest_user_message_truncated(
    engine: AsyncEngine, repo: SqlAlchemyConversationRepository
) -> None:
    await _seed_documents(engine)
    base = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    await _insert_conversation(engine, "conv-1", "alice", DOC_AAA, base)
    long_user_text = "x" * (LAST_MESSAGE_PREVIEW_MAX_CHARS + 25)
    await _insert_message(
        engine,
        "m-user-old",
        "conv-1",
        Role.USER,
        "first user line",
        base + timedelta(minutes=1),
    )
    await _insert_message(
        engine,
        "m-assistant",
        "conv-1",
        Role.ASSISTANT,
        "an assistant reply",
        base + timedelta(minutes=2),
    )
    await _insert_message(
        engine,
        "m-user-new",
        "conv-1",
        Role.USER,
        long_user_text,
        base + timedelta(minutes=3),
    )

    summaries = await repo.list_for_user("alice")

    assert len(summaries) == 1
    assert summaries[0].last_message_preview == "x" * LAST_MESSAGE_PREVIEW_MAX_CHARS


async def test_list_for_user_falls_back_to_created_at_when_no_messages(
    engine: AsyncEngine, repo: SqlAlchemyConversationRepository
) -> None:
    await _seed_documents(engine)
    created = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    await _insert_conversation(engine, "conv-empty", "alice", DOC_AAA, created)

    summaries = await repo.list_for_user("alice")

    assert len(summaries) == 1
    assert summaries[0].last_message_preview == ""
    assert summaries[0].last_message_at == created


async def test_list_for_user_isolates_other_users(
    engine: AsyncEngine, repo: SqlAlchemyConversationRepository
) -> None:
    await _seed_documents(engine)
    base = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    await _insert_conversation(engine, "conv-alice", "alice", DOC_AAA, base)
    await _insert_conversation(engine, "conv-bob", "bob", DOC_BBB, base)

    alice_summaries = await repo.list_for_user("alice")
    bob_summaries = await repo.list_for_user("bob")

    assert [s.id for s in alice_summaries] == ["conv-alice"]
    assert [s.id for s in bob_summaries] == ["conv-bob"]


async def test_get_messages_returns_messages_in_chronological_order(
    engine: AsyncEngine, repo: SqlAlchemyConversationRepository
) -> None:
    await _seed_documents(engine)
    base = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    await _insert_conversation(engine, "conv-1", "alice", DOC_AAA, base)
    await _insert_message(
        engine,
        "m-2",
        "conv-1",
        Role.ASSISTANT,
        "second",
        base + timedelta(seconds=20),
    )
    await _insert_message(
        engine,
        "m-1",
        "conv-1",
        Role.USER,
        "first",
        base + timedelta(seconds=10),
    )

    messages = await repo.get_messages("conv-1", "alice")

    assert messages is not None
    assert [m.id for m in messages] == ["m-1", "m-2"]
    assert [m.role for m in messages] == [Role.USER, Role.ASSISTANT]


async def test_get_messages_returns_none_for_cross_user_access(
    engine: AsyncEngine, repo: SqlAlchemyConversationRepository
) -> None:
    await _seed_documents(engine)
    base = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    await _insert_conversation(engine, "conv-1", "alice", DOC_AAA, base)
    await _insert_message(
        engine, "m-1", "conv-1", Role.USER, "hi", base + timedelta(seconds=1)
    )

    got = await repo.get_messages("conv-1", "mallory")

    assert got is None


async def test_get_messages_returns_none_for_unknown_conversation(
    engine: AsyncEngine, repo: SqlAlchemyConversationRepository
) -> None:
    del engine

    got = await repo.get_messages("conv-nonexistent", "alice")

    assert got is None
