"""
Миграция для добавления таблицы prediction_history.
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
    """Добавляем таблицу prediction_history"""
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    
    log.info("Создаём таблицу prediction_history...")
    
    async with engine.begin() as conn:
        # Создаём все таблицы, которых ещё нет
        await conn.run_sync(Base.metadata.create_all)
    
    log.info("✅ Таблица prediction_history создана (или уже существовала)")
    
    # Проверяем существование таблицы
    async with engine.begin() as conn:
        result = await conn.run_sync(
            lambda sync_conn: sync_conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='prediction_history'")
            ).fetchone()
        )
        
        if result:
            log.info(f"✅ Таблица prediction_history существует: {result[0]}")
            
            # Проверяем структуру таблицы
            columns_result = await conn.run_sync(
                lambda sync_conn: sync_conn.execute(
                    text("PRAGMA table_info(prediction_history)")
                ).fetchall()
            )
            log.info(f"Структура таблицы prediction_history:")
            for col in columns_result:
                log.info(f"  - {col[1]} ({col[2]})")
        else:
            log.error("❌ Таблица prediction_history не создана")
    
    # Закрываем соединение
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())