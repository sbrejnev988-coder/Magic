"""
Р”РІРёР¶РѕРє Р±Р°Р·С‹ РґР°РЅРЅС‹С… SQLAlchemy СЃ connection pooling
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import QueuePool
from typing import AsyncGenerator


def create_engine(database_url: str, echo: bool = False):
    """
    РЎРѕР·РґР°РЅРёРµ async engine СЃ РЅР°СЃС‚СЂРѕРµРЅРЅС‹Рј connection pooling
    
    Args:
        database_url: URL Р±Р°Р·С‹ РґР°РЅРЅС‹С…
        echo: Р’С‹РІРѕРґ SQL Р·Р°РїСЂРѕСЃРѕРІ РІ Р»РѕРі
    """
    # РќР°СЃС‚СЂРѕР№РєРё connection pooling
    pool_settings = {
        "poolclass": QueuePool,
        "pool_size": 10,              # РњРёРЅРёРјР°Р»СЊРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СЃРѕРµРґРёРЅРµРЅРёР№
        "max_overflow": 20,            # РњР°РєСЃРёРјР°Р»СЊРЅРѕРµ РєРѕР»РёС‡РµСЃС‚РІРѕ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹С… СЃРѕРµРґРёРЅРµРЅРёР№
        "pool_timeout": 30,            # РўР°Р№РјР°СѓС‚ РѕР¶РёРґР°РЅРёСЏ СЃРІРѕР±РѕРґРЅРѕРіРѕ СЃРѕРµРґРёРЅРµРЅРёСЏ (СЃРµРєСѓРЅРґС‹)
        "pool_recycle": 3600,          # РџРµСЂРµРёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ СЃРѕРµРґРёРЅРµРЅРёР№ РєР°Р¶РґС‹Р№ С‡Р°СЃ
        "pool_pre_ping": True,          # РџСЂРѕРІРµСЂРєР° СЃРѕРµРґРёРЅРµРЅРёСЏ РїРµСЂРµРґ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј
    }
    
    # Р”Р»СЏ SQLite РЅРµ РёСЃРїРѕР»СЊР·СѓРµРј pooling
    if "sqlite" in database_url:
        return create_async_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False}
        )
    
    # Р”Р»СЏ PostgreSQL РёСЃРїРѕР»СЊР·СѓРµРј РїРѕР»РЅРѕС†РµРЅРЅС‹Р№ pooling
    return create_async_engine(
        database_url,
        echo=echo,
        **pool_settings
    )


def get_session_maker(engine) -> async_sessionmaker:
    """
    РЎРѕР·РґР°РЅРёРµ session maker РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ Р‘Р”
    
    Args:
        engine: SQLAlchemy async engine
    
    Returns:
        async_sessionmaker: Р¤Р°Р±СЂРёРєР° СЃРµСЃСЃРёР№
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
    Context manager РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ СЃРµСЃСЃРёРё Р‘Р”
    
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
