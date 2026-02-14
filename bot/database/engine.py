"""
Настройка подключения к базе данных
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def create_engine(database_url: str):
    """Создать асинхронный движок SQLAlchemy"""
    # Заменяем синхронный драйвер на асинхронный (если нужно)
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("sqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    return engine


def get_session_maker(engine):
    """Создать фабрику сессий"""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)