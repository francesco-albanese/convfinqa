from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.auth.cognito_jwks import CognitoJwksAdapter
from convfinqa.adapters.cache.postgres import PostgresCacheAdapter
from convfinqa.adapters.llm.litellm_adapter import LiteLLMAdapter
from convfinqa.adapters.persistence.documents_repo import SqlAlchemyDocumentsRepository
from convfinqa.adapters.persistence.sqlalchemy.engine import (
    create_engine,
    create_session_factory,
)
from convfinqa.adapters.persistence.sqlalchemy.lock import SqlAlchemyConversationLock
from convfinqa.adapters.persistence.sqlalchemy.repository import (
    SqlAlchemyConversationRepository,
    SqlAlchemyDocumentRepository,
)
from convfinqa.adapters.persistence.sqlalchemy.user_lookup import SqlAlchemyUserLookup
from convfinqa.adapters.rate_limit.postgres import PostgresRateLimitAdapter
from convfinqa.application.use_cases.get_chat_messages import GetChatMessagesUseCase
from convfinqa.application.use_cases.get_document import GetDocumentUseCase
from convfinqa.application.use_cases.list_chats import ListChatsUseCase
from convfinqa.application.use_cases.list_documents import ListDocumentsUseCase
from convfinqa.application.use_cases.send_message import SendMessageUseCase
from convfinqa.config import Settings
from convfinqa.domain.ports.cache import CachePort
from convfinqa.domain.ports.documents_port import DocumentsPort
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.lock import ConversationLockPort
from convfinqa.domain.ports.rate_limit import RateLimitPort
from convfinqa.domain.ports.repository import (
    ConversationRepository,
    DocumentRepository,
)
from convfinqa.domain.ports.session import SessionPort
from convfinqa.logging import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    llm: LLMPort
    conversations: ConversationRepository
    documents: DocumentRepository
    documents_port: DocumentsPort
    locks: ConversationLockPort
    send_message: SendMessageUseCase
    list_documents: ListDocumentsUseCase
    get_document: GetDocumentUseCase
    list_chats: ListChatsUseCase
    get_chat_messages: GetChatMessagesUseCase
    cache: CachePort
    rate_limit: RateLimitPort
    session: SessionPort | None = None

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
        documents_port: DocumentsPort = SqlAlchemyDocumentsRepository(session_factory)
        locks: ConversationLockPort = SqlAlchemyConversationLock(session_factory)
        send_message = SendMessageUseCase(
            llm=llm,
            conversations=conversations,
            documents=documents,
            locks=locks,
            system_prompt_framing=settings.system_prompt,
        )
        list_documents = ListDocumentsUseCase(documents=documents_port)
        get_document = GetDocumentUseCase(documents=documents_port)
        list_chats = ListChatsUseCase(conversations=conversations)
        get_chat_messages = GetChatMessagesUseCase(conversations=conversations)
        session: SessionPort | None = None
        if settings.cognito_user_pool_id and settings.cognito_client_id:
            session = CognitoJwksAdapter(
                jwks_url=(
                    f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
                    f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
                ),
                issuer=(
                    f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
                    f"/{settings.cognito_user_pool_id}"
                ),
                client_id=settings.cognito_client_id,
                find_user_by_sub=SqlAlchemyUserLookup(session_factory),
            )
        if session is None:
            _log.warning(
                "Cognito session disabled: COGNITO_USER_POOL_ID or COGNITO_CLIENT_ID "
                "not set. Auth middleware is bypassed; X-User-Id header is trusted as "
                "identity. Do NOT run in this state in production.",
            )
        cache: CachePort = PostgresCacheAdapter(session_factory)
        rate_limit: RateLimitPort = PostgresRateLimitAdapter(session_factory)
        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            llm=llm,
            conversations=conversations,
            documents=documents,
            documents_port=documents_port,
            locks=locks,
            send_message=send_message,
            list_documents=list_documents,
            get_document=get_document,
            list_chats=list_chats,
            get_chat_messages=get_chat_messages,
            cache=cache,
            rate_limit=rate_limit,
            session=session,
        )

    @classmethod
    def for_testing(
        cls,
        settings: Settings,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        llm: LLMPort,
        session: SessionPort | None = None,
        cache: CachePort | None = None,
        rate_limit: RateLimitPort | None = None,
    ) -> "Container":
        conversations: ConversationRepository = SqlAlchemyConversationRepository(
            session_factory
        )
        documents: DocumentRepository = SqlAlchemyDocumentRepository(session_factory)
        documents_port: DocumentsPort = SqlAlchemyDocumentsRepository(session_factory)
        locks: ConversationLockPort = SqlAlchemyConversationLock(session_factory)
        send_message = SendMessageUseCase(
            llm=llm,
            conversations=conversations,
            documents=documents,
            locks=locks,
            system_prompt_framing=settings.system_prompt,
        )
        list_documents = ListDocumentsUseCase(documents=documents_port)
        get_document = GetDocumentUseCase(documents=documents_port)
        list_chats = ListChatsUseCase(conversations=conversations)
        get_chat_messages = GetChatMessagesUseCase(conversations=conversations)
        resolved_cache: CachePort = cache if cache is not None else PostgresCacheAdapter(session_factory)
        resolved_rate_limit: RateLimitPort = rate_limit if rate_limit is not None else PostgresRateLimitAdapter(session_factory)
        return cls(
            settings=settings,
            engine=engine,
            session_factory=session_factory,
            llm=llm,
            conversations=conversations,
            documents=documents,
            documents_port=documents_port,
            locks=locks,
            send_message=send_message,
            list_documents=list_documents,
            get_document=get_document,
            list_chats=list_chats,
            get_chat_messages=get_chat_messages,
            cache=resolved_cache,
            rate_limit=resolved_rate_limit,
            session=session,
        )
