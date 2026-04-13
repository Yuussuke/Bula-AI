from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.base import Base


__all__ = ["Base", "engine", "async_session_factory", "get_db", "close_engine"]


engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)


async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    await engine.dispose()
