from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.llm.litellm_adapter import LiteLLMAdapter
from convfinqa.adapters.persistence.sqlalchemy.engine import (
    create_engine,
    create_session_factory,
)
from convfinqa.adapters.persistence.sqlalchemy.lock import SqlAlchemyConversationLock
from convfinqa.adapters.persistence.sqlalchemy.repository import (
    SqlAlchemyConversationRepository,
    SqlAlchemyDocumentRepository,
)
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.config import Settings
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    llm: LLMPort
    conversations: ConversationRepository
    documents: DocumentRepository
    locks: ConversationLockPort
    send_message: SendMessageUseCase

    @classmethod
    def bootstrap_application(cls, settings: Settings) -> "Container":
        engine = create_engine(settings.database_url)
        session_factory = create_session_factory(engine)
        llm: LLMPort = LiteLLMAdapter(
            model=settings.llm_model,
            request_timeout_seconds=settings.llm_request_timeout_seconds,
            max_output_tokens=settings.llm_max_output_tokens,
        )
        conversations: ConversationRepository = SqlAlchemyConversationRepository(
            session_factory
        )
        documents: DocumentRepository = SqlAlchemyDocumentRepository(session_factory)
        locks: ConversationLockPort = SqlAlchemyConversationLock(session_factory)
        send_message = SendMessageUseCase(
            llm=llm,
            conversations=conversations,
            documents=documents,
            locks=locks,
            system_prompt_framing=settings.system_prompt,
        )
        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            llm=llm,
            conversations=conversations,
            documents=documents,
            locks=locks,
            send_message=send_message,
        )

    @classmethod
    def for_testing(
        cls,
        settings: Settings,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        llm: LLMPort,
    ) -> "Container":
        conversations: ConversationRepository = SqlAlchemyConversationRepository(
            session_factory
        )
        documents: DocumentRepository = SqlAlchemyDocumentRepository(session_factory)
        locks: ConversationLockPort = SqlAlchemyConversationLock(session_factory)
        send_message = SendMessageUseCase(
            llm=llm,
            conversations=conversations,
            documents=documents,
            locks=locks,
            system_prompt_framing=settings.system_prompt,
        )
        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            llm=llm,
            conversations=conversations,
            documents=documents,
            locks=locks,
            send_message=send_message,
        )
