import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from convfinqa.adapters.persistence.sqlalchemy.models import (
    ConversationOrm,
    DocumentOrm,
    MessageOrm,
)
from convfinqa.domain.entities import (
    Conversation,
    ConversationSummary,
    Document,
    DocumentSummary,
    Message,
)
from convfinqa.domain.value_objects import Role, StopReason

LAST_MESSAGE_PREVIEW_MAX_CHARS = 80

LIST_CHATS_SQL = text(
    "SELECT c.id, "
    "       d.id AS doc_id, d.ticker, d.year, d.page, d.title, "
    "       COALESCE(LEFT(latest_user.content, :preview_max), '') "
    "         AS last_message_preview, "
    "       COALESCE(latest_any.created_at, c.created_at) "
    "         AS last_message_at, "
    "       c.title AS conversation_title "
    "FROM conversations c "
    "JOIN documents d ON d.id = c.document_id "
    "LEFT JOIN LATERAL ( "
    "  SELECT content FROM messages m "
    "  WHERE m.conversation_id = c.id AND m.role = 'user' "
    "  ORDER BY m.created_at DESC, m.id DESC LIMIT 1 "
    ") AS latest_user ON TRUE "
    "LEFT JOIN LATERAL ( "
    "  SELECT created_at FROM messages m "
    "  WHERE m.conversation_id = c.id "
    "  ORDER BY m.created_at DESC, m.id DESC LIMIT 1 "
    ") AS latest_any ON TRUE "
    "WHERE c.user_id = :user_id "
    "ORDER BY last_message_at DESC, c.id ASC"
)


def new_conversation_id() -> str:
    return f"conv_{uuid4().hex}"


def _to_message(orm: MessageOrm) -> Message:
    stop = StopReason(orm.stop_reason) if orm.stop_reason else None
    sigs: dict[str, str] | None = None
    if orm.reasoning_signatures is not None:
        sigs = {k: str(v) for k, v in orm.reasoning_signatures.items()}
    return Message(
        id=orm.id,
        conversation_id=orm.conversation_id,
        role=Role(orm.role),
        content=orm.content,
        created_at=orm.created_at,
        stop_reason=stop,
        parts=orm.parts,
        reasoning_signatures=sigs,
    )


def _to_conversation(orm: ConversationOrm) -> Conversation:
    return Conversation(
        id=orm.id,
        user_id=str(orm.user_id) if orm.user_id is not None else "",
        document_id=orm.document_id,
        created_at=orm.created_at,
        messages=tuple(_to_message(m) for m in orm.messages),
        title=orm.title,
    )


def _to_document(orm: DocumentOrm) -> Document:
    return Document(
        id=orm.id,
        ticker=orm.ticker,
        year=orm.year,
        page=orm.page,
        title=orm.title,
        pre_text=orm.pre_text,
        post_text=orm.post_text,
        table_data=orm.table_data,
        column_order=(
            tuple(orm.column_order) if orm.column_order is not None else None
        ),
    )


class SqlAlchemyConversationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> Conversation | None:
        async with self._session_factory() as session:
            stmt = (
                select(ConversationOrm)
                .where(
                    ConversationOrm.id == conversation_id,
                    ConversationOrm.user_id == user_id,
                )
                .options(selectinload(ConversationOrm.messages))
            )
            result = await session.execute(stmt)
            orm = result.scalar_one_or_none()
            if orm is None:
                return None
            return _to_conversation(orm)

    async def create(self, user_id: uuid.UUID, document_id: str) -> Conversation:
        async with self._session_factory() as session:
            orm = ConversationOrm(
                id=new_conversation_id(),
                user_id=user_id,
                document_id=document_id,
                created_at=datetime.now(UTC),
            )
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
            return Conversation(
                id=orm.id,
                user_id=str(orm.user_id) if orm.user_id is not None else "",
                document_id=orm.document_id,
                created_at=orm.created_at,
                messages=(),
                title=orm.title,
            )

    async def append_message(self, conversation_id: str, message: Message) -> None:
        async with self._session_factory() as session:
            orm = MessageOrm(
                id=message.id,
                conversation_id=conversation_id,
                role=message.role.value,
                content=message.content,
                stop_reason=message.stop_reason.value if message.stop_reason else None,
                created_at=message.created_at,
                parts=message.parts,
                reasoning_signatures=message.reasoning_signatures,
            )
            session.add(orm)
            await session.commit()

    async def list_for_user(
        self, user_id: uuid.UUID
    ) -> tuple[ConversationSummary, ...]:
        async with self._session_factory() as session:
            result = await session.execute(
                LIST_CHATS_SQL,
                {
                    "user_id": user_id,
                    "preview_max": LAST_MESSAGE_PREVIEW_MAX_CHARS,
                },
            )
            rows: list[Any] = list(result.all())
        return tuple(
            ConversationSummary(
                id=row[0],
                document=DocumentSummary(
                    id=row[1],
                    ticker=row[2],
                    year=row[3],
                    page=row[4],
                    title=row[5],
                ),
                last_message_preview=row[6],
                last_message_at=row[7],
                title=row[8],
            )
            for row in rows
        )

    async def get_messages(
        self, conversation_id: str, user_id: uuid.UUID
    ) -> tuple[Message, ...] | None:
        async with self._session_factory() as session:
            owner_stmt = select(ConversationOrm.id).where(
                ConversationOrm.id == conversation_id,
                ConversationOrm.user_id == user_id,
            )
            owner_row = (await session.execute(owner_stmt)).scalar_one_or_none()
            if owner_row is None:
                return None
            messages_stmt = (
                select(MessageOrm)
                .where(MessageOrm.conversation_id == conversation_id)
                .order_by(MessageOrm.created_at, MessageOrm.id)
            )
            result = await session.execute(messages_stmt)
            return tuple(_to_message(m) for m in result.scalars().all())

    async def set_title(self, conversation_id: str, title: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(ConversationOrm)
                .where(ConversationOrm.id == conversation_id)
                .values(title=title)
            )
            await session.commit()


class SqlAlchemyDocumentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, document_id: str) -> Document | None:
        async with self._session_factory() as session:
            stmt = select(DocumentOrm).where(DocumentOrm.id == document_id)
            result = await session.execute(stmt)
            orm = result.scalar_one_or_none()
            if orm is None:
                return None
            return _to_document(orm)
