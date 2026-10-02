from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.platform.core.config import settings

engine = create_async_engine(
    settings.db_connection,
    echo=settings.sqlalchemy_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    pool_recycle=settings.db_pool_recycle,
)
ASYNC_SESSION_LOCAL = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase): ...


async def get_db() -> AsyncGenerator[AsyncSession]:
    """One transaction per request: committed when the endpoint returns,
    rolled back if it raises."""
    async with ASYNC_SESSION_LOCAL(expire_on_commit=True) as db:
        async with db.begin():
            yield db


# Always depend on the request session through this alias, never on
# `Depends(get_db)` directly. `scope="function"` commits when the endpoint
# returns, before the response is sent. FastAPI's default ("request") would
# commit only after the response and its background tasks: the client would
# be told a write succeeded before it was committed, emails would go out
# first, and the transaction (and its row locks) would stay open while they
# are sent. One alias also keeps every dependent on the same cached session -
# FastAPI caches per scope, so mixed scopes would open two sessions.
DbSession = Annotated[AsyncSession, Depends(get_db, scope="function")]
