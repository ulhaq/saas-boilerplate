from collections.abc import AsyncGenerator

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
    async with ASYNC_SESSION_LOCAL(expire_on_commit=True) as db:
        async with db.begin():
            yield db
