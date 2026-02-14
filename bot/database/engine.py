"""
Движок базы данных SQLAlchemy с connection pooling
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from typing import AsyncGenerator


def create_engine(database_url: str, echo: bool = False):
    """
    Создание async engine с настроенным connection pooling
    
    Args:
        database_url: URL базы данных
        echo: Вывод SQL запросов в лог
    """
    # Настройки connection pooling
    pool_settings = {
        "poolclass": QueuePool,
        "pool_size": 10,              # Минимальное количество соединений
        "max_overflow": 20,            # Максимальное количество дополнительных соединений
        "pool_timeout": 30,            # Таймаут ожидания свободного соединения (секунды)
        "pool_recycle": 3600,          # Переиспользование соединений каждый час
        "pool_pre_ping": True,          # Проверка соединения перед использованием
    }
    
    # Для SQLite не используем pooling
    if "sqlite" in database_url:
        return create_async_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False}
        )
    
    # Для PostgreSQL используем полноценный pooling
    return create_async_engine(
        database_url,
        echo=echo,
        **pool_settings
    )


def get_session_maker(engine) -> async_sessionmaker:
    """
    Создание session maker для работы с БД
    
    Args:
        engine: SQLAlchemy async engine
    
    Returns:
        async_sessionmaker: Фабрика сессий
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )


async def get_session(session_maker: async_sessionmaker) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager для получения сессии БД
    
    Usage:
        async with get_session(session_maker) as session:
            # work with session
    """
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
