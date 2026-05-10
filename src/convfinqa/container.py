from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.llm.litellm_adapter import LiteLLMAdapter
from convfinqa.adapters.persistence.sqlalchemy.engine import (
    create_engine,
    create_session_factory,
)
from convfinqa.adapters.persistence.sqlalchemy.repository import (
    SqlAlchemyConversationRepository,
)
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.config import Settings
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.repository import ConversationRepository


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    llm: LLMPort
    conversations: ConversationRepository
    send_message: SendMessageUseCase

    @classmethod
    def bootstrap_application(cls, settings: Settings) -> "Container":
        engine = create_engine(settings.database_url)
        session_factory = create_session_factory(engine)
        llm: LLMPort = LiteLLMAdapter(model=settings.llm_model)
        conversations: ConversationRepository = SqlAlchemyConversationRepository(
            session_factory
        )
        send_message = SendMessageUseCase(
            llm=llm,
            conversations=conversations,
            system_prompt=settings.system_prompt,
        )
        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            llm=llm,
            conversations=conversations,
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
        send_message = SendMessageUseCase(
            llm=llm,
            conversations=conversations,
            system_prompt=settings.system_prompt,
        )
        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            llm=llm,
            conversations=conversations,
            send_message=send_message,
        )
