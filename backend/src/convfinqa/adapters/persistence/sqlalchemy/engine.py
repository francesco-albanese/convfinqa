from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    # pool_recycle=300 forces connection renewal before Aurora's idle-connection
    # timeout, which is the prerequisite for Aurora Serverless v2 to auto-pause.
    # pool_size + max_overflow bounds concurrent asyncpg connections per worker;
    # the ConversationLockPort holds one open connection per in-flight LLM call.
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=2,
        max_overflow=2,
        future=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
