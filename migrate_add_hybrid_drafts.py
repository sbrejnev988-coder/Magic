"""
Миграция для добавления таблицы hybrid_drafts.
"""

import asyncio
import logging
from sqlalchemy import text
from bot.database.engine import create_engine, get_session_maker
from bot.models.base import Base
import bot.models  # регистрация всех моделей
from bot.config import Settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def main():
    """Добавляем таблицу hybrid_drafts"""
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    
    log.info("Создаём таблицу hybrid_drafts...")
    
    async with engine.begin() as conn:
        # Создаём все таблицы, которых ещё нет
        await conn.run_sync(Base.metadata.create_all)
    
    log.info("✅ Таблица hybrid_drafts создана (или уже существовала)")
    
    # Проверяем существование таблицы
    async with engine.begin() as conn:
        result = await conn.run_sync(
            lambda sync_conn: sync_conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='hybrid_drafts'")
            ).fetchone()
        )
        
        if result:
            log.info(f"✅ Таблица hybrid_drafts существует: {result[0]}")
        else:
            log.error("❌ Таблица hybrid_drafts не создана")


if __name__ == "__main__":
    asyncio.run(main())