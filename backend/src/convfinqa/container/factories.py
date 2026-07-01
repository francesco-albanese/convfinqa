from collections.abc import Awaitable, Callable

from langfuse import Langfuse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from convfinqa.adapters.auth.cognito_jwks import CognitoJwksAdapter
from convfinqa.adapters.cache.postgres import PostgresCacheAdapter
from convfinqa.adapters.persistence.documents_repo import SqlAlchemyDocumentsRepository
from convfinqa.adapters.persistence.sqlalchemy.lock import SqlAlchemyConversationLock
from convfinqa.adapters.persistence.sqlalchemy.repository import (
    SqlAlchemyConversationRepository,
    SqlAlchemyDocumentRepository,
)
from convfinqa.adapters.persistence.sqlalchemy.user_lookup import SqlAlchemyUserLookup
from convfinqa.adapters.prompts.langfuse_provider import LangfusePromptProvider
from convfinqa.adapters.prompts.local_file import LocalFilePromptProvider
from convfinqa.adapters.rate_limit.postgres import PostgresRateLimitAdapter
from convfinqa.application.use_cases.delete_conversation import (
    DeleteConversationUseCase,
)
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
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.domain.ports.prompts import PromptProviderPort
from convfinqa.domain.ports.rate_limit import RateLimitPort
from convfinqa.domain.ports.repository import ConversationRepository, DocumentRepository
from convfinqa.domain.ports.session import SessionPort, UserRecord

UserLookup = Callable[[str], Awaitable[UserRecord | None]]


def build_prompt_provider(settings: Settings) -> PromptProviderPort:
    if settings.langfuse_enabled and settings.langfuse_public_key and settings.langfuse_secret_key:
        client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            tracing_enabled=False,
        )
        return LangfusePromptProvider(client)
    return LocalFilePromptProvider()


def build_persistence(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[
    ConversationRepository,
    DocumentRepository,
    DocumentsPort,
    ConversationLockPort,
    UserLookup,
]:
    conversations: ConversationRepository = SqlAlchemyConversationRepository(
        session_factory
    )
    documents: DocumentRepository = SqlAlchemyDocumentRepository(session_factory)
    documents_port: DocumentsPort = SqlAlchemyDocumentsRepository(session_factory)
    locks: ConversationLockPort = SqlAlchemyConversationLock(session_factory)
    user_lookup: UserLookup = SqlAlchemyUserLookup(session_factory)
    return conversations, documents, documents_port, locks, user_lookup


def build_session(
    settings: Settings,
    user_lookup: UserLookup,
) -> SessionPort | None:
    if settings.cognito_user_pool_id and settings.cognito_client_id:
        return CognitoJwksAdapter(
            jwks_url=(
                f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
                f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
            ),
            issuer=(
                f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
                f"/{settings.cognito_user_pool_id}"
            ),
            client_id=settings.cognito_client_id,
            find_user_by_sub=user_lookup,
        )
    return None


def build_use_cases(
    llm: LLMPort,
    conversations: ConversationRepository,
    documents: DocumentRepository,
    documents_port: DocumentsPort,
    locks: ConversationLockPort,
    prompt_provider: PromptProviderPort,
    settings: Settings,
    observability: ObservabilityPort,
    system_prompt_label: str = "production",
) -> tuple[
    SendMessageUseCase,
    ListDocumentsUseCase,
    GetDocumentUseCase,
    ListChatsUseCase,
    GetChatMessagesUseCase,
    DeleteConversationUseCase,
]:
    send_message = SendMessageUseCase(
        llm=llm,
        conversations=conversations,
        documents=documents,
        locks=locks,
        prompt_provider=prompt_provider,
        observability=observability,
        llm_model=settings.llm_model,
        environment=settings.environment,
        system_prompt_label=system_prompt_label,
    )
    list_documents = ListDocumentsUseCase(documents=documents_port)
    get_document = GetDocumentUseCase(documents=documents_port)
    list_chats = ListChatsUseCase(conversations=conversations)
    get_chat_messages = GetChatMessagesUseCase(conversations=conversations)
    delete_conversation = DeleteConversationUseCase(conversations=conversations)
    return (
        send_message,
        list_documents,
        get_document,
        list_chats,
        get_chat_messages,
        delete_conversation,
    )


def build_pg_adapters(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[CachePort, RateLimitPort]:
    return PostgresCacheAdapter(session_factory), PostgresRateLimitAdapter(
        session_factory
    )
