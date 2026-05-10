from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    # The ConversationLockPort holds an open advisory-xact lock transaction (one
    # asyncpg connection) for the duration of each in-flight LLM call. Concurrent
    # in-flight chats per worker are therefore bounded by pool_size + max_overflow.
    # Tune the pool here if expected concurrency exceeds SQLAlchemy's defaults
    # (5 + 10 overflow at the time of writing).
    return create_async_engine(database_url, pool_pre_ping=True, future=True)


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
