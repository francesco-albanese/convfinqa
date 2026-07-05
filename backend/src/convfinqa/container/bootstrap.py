from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from convfinqa.adapters.llm.litellm_adapter import LiteLLMAdapter
from convfinqa.adapters.observability.langfuse_client import init_langfuse
from convfinqa.adapters.observability.tracer_provider import init_tracer_provider
from convfinqa.adapters.persistence.sqlalchemy.engine import (
    create_engine,
    create_session_factory,
)
from convfinqa.config import Settings
from convfinqa.container.container import Container
from convfinqa.container.factories import (
    build_persistence,
    build_pg_adapters,
    build_session,
    build_use_cases,
)
from convfinqa.domain.ports.cache import CachePort
from convfinqa.domain.ports.llm import LLMPort
from convfinqa.domain.ports.observability import ObservabilityPort
from convfinqa.domain.ports.rate_limit import RateLimitPort
from convfinqa.domain.ports.session import SessionPort
from convfinqa.logging import get_logger

_log = get_logger(__name__)


def bootstrap_application(settings: Settings) -> Container:
    init_tracer_provider(settings)
    observability = init_langfuse(settings)
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    llm: LLMPort = LiteLLMAdapter(
        model=settings.llm_model,
        request_timeout_seconds=settings.llm_request_timeout_seconds,
        max_output_tokens=settings.llm_max_output_tokens,
    )
    conversations, documents, documents_port, locks, user_lookup = build_persistence(
        session_factory
    )
    session = build_session(settings, user_lookup)
    if session is None:
        _log.warning(
            "Cognito session disabled: COGNITO_USER_POOL_ID or COGNITO_CLIENT_ID "
            "not set. Auth middleware is bypassed; X-User-Id header is trusted as "
            "identity. Do NOT run in this state in production.",
        )
    cache, rate_limit = build_pg_adapters(session_factory)
    (
        send_message,
        list_documents,
        get_document,
        list_chats,
        get_chat_messages,
        delete_conversation,
    ) = build_use_cases(
        llm,
        conversations,
        documents,
        documents_port,
        locks,
        settings,
        observability,
        rate_limit,
    )
    return Container(
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
        delete_conversation=delete_conversation,
        observability=observability,
        cache=cache,
        rate_limit=rate_limit,
        session=session,
    )


def for_testing(
    settings: Settings,
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
    llm: LLMPort,
    session: SessionPort | None = None,
    cache: CachePort | None = None,
    rate_limit: RateLimitPort | None = None,
    observability: ObservabilityPort | None = None,
) -> Container:
    resolved_observability: ObservabilityPort
    if observability is None:
        init_tracer_provider(settings)
        resolved_observability = init_langfuse(settings)
    else:
        resolved_observability = observability
    conversations, documents, documents_port, locks, _ = build_persistence(
        session_factory
    )
    pg_cache, pg_rate_limit = build_pg_adapters(session_factory)
    resolved_cache: CachePort = cache if cache is not None else pg_cache
    resolved_rate_limit: RateLimitPort = (
        rate_limit if rate_limit is not None else pg_rate_limit
    )
    (
        send_message,
        list_documents,
        get_document,
        list_chats,
        get_chat_messages,
        delete_conversation,
    ) = build_use_cases(
        llm,
        conversations,
        documents,
        documents_port,
        locks,
        settings,
        resolved_observability,
        resolved_rate_limit,
    )
    return Container(
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
        delete_conversation=delete_conversation,
        observability=resolved_observability,
        cache=resolved_cache,
        rate_limit=resolved_rate_limit,
        session=session,
    )
