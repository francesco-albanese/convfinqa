from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from convfinqa.adapters.persistence.sqlalchemy.models import (
    ConversationOrm,
    DocumentOrm,
    MessageOrm,
)
from convfinqa.domain.entities import Conversation, Document, Message
from convfinqa.domain.value_objects import Role, StopReason


def new_conversation_id() -> str:
    return f"conv_{uuid4().hex}"


def _to_message(orm: MessageOrm) -> Message:
    stop = StopReason(orm.stop_reason) if orm.stop_reason else None
    return Message(
        id=orm.id,
        conversation_id=orm.conversation_id,
        role=Role(orm.role),
        content=orm.content,
        created_at=orm.created_at,
        stop_reason=stop,
    )


def _to_conversation(orm: ConversationOrm) -> Conversation:
    return Conversation(
        id=orm.id,
        user_id=orm.user_id,
        document_id=orm.document_id,
        created_at=orm.created_at,
        messages=tuple(_to_message(m) for m in orm.messages),
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

    async def get(self, conversation_id: str, user_id: str) -> Conversation | None:
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

    async def create(self, user_id: str, document_id: str) -> Conversation:
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
                user_id=orm.user_id,
                document_id=orm.document_id,
                created_at=orm.created_at,
                messages=(),
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
            )
            session.add(orm)
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
