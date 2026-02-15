"""
Движок базы данных SQLAlchemy с connection pooling.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import QueuePool, NullPool

logger = logging.getLogger(__name__)


def create_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """
    Создание async engine с настроенным connection pooling.

    - SQLite: NullPool (потокобезопасность)
    - PostgreSQL: QueuePool с разумными лимитами
    """
    if "sqlite" in database_url:
        logger.info(f"🗄️ SQLite engine: {database_url}")
        return create_async_engine(
            database_url,
            echo=echo,
            poolclass=NullPool,  # SQLite не поддерживает QueuePool
            connect_args={"check_same_thread": False},
        )

    # PostgreSQL / другие СУБД
    logger.info(f"🐘 PostgreSQL engine: pool_size=5, max_overflow=10")
    return create_async_engine(
        database_url,
        echo=echo,
        poolclass=QueuePool,
        pool_size=5,           # 5 постоянных соединений (было 10)
        max_overflow=10,       # +10 пиковых (было 20)
        pool_timeout=30,
        pool_recycle=3600,     # Пересоздание каждый час
        pool_pre_ping=True,    # Проверка перед использованием
    )


def get_session_maker(engine: AsyncEngine) -> async_sessionmaker:
    """Фабрика сессий."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_session(
    session_maker: async_sessionmaker,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager для получения сессии БД.

    ВАЖНО: Не коммитит автоматически!
    Handler должен вызвать session.commit() явно после записи.
    """
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            logger.error("❌ Сессия откачена (rollback)")
            raise
        finally:
            await session.close()
