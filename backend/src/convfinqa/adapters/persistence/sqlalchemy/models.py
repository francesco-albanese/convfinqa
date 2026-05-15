import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

DOCUMENTS_TSVECTOR_EXPRESSION = (
    "to_tsvector('english', "
    "coalesce(title,'') || ' ' || "
    "coalesce(ticker,'') || ' ' || "
    "coalesce(pre_text,''))"
)


class Base(DeclarativeBase):
    pass


class ConversationOrm(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_conversations_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("documents.id", name="fk_conversations_document_id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    messages: Mapped[list["MessageOrm"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="MessageOrm.created_at",
    )

    __table_args__ = (
        Index("ix_conversations_user_id_created_at", "user_id", "created_at"),
        Index("ix_conversations_document_id", "document_id"),
    )


class MessageOrm(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    stop_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[ConversationOrm] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','system')", name="ck_messages_role"
        ),
        Index(
            "ix_messages_conversation_id_created_at", "conversation_id", "created_at"
        ),
    )


class DocumentOrm(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    ticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    pre_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    table_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    column_order: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(DOCUMENTS_TSVECTOR_EXPRESSION, persisted=True),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_documents_search_tsv", "search_tsv", postgresql_using="gin"),
        Index("ix_documents_year", "year"),
        Index("ix_documents_ticker_year", "ticker", "year"),
    )


class UserOrm(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    cognito_sub: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
