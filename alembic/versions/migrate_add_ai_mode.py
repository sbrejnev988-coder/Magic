#!/usr/bin/env python3
"""
Скрипт миграции для добавления колонок ai_mode и hybrid_mode в таблицу user_settings.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import Settings
from bot.database.engine import create_engine, get_session_maker
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def migrate():
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    session_maker = get_session_maker(engine)
    
    async with engine.begin() as conn:
        # Проверяем существование колонок
        result = await conn.execute(text("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='user_settings'
        """))
        table_sql = result.scalar()
        log.info(f"Table schema: {table_sql}")
        
        # Добавляем колонку ai_mode, если её нет
        if 'ai_mode' not in table_sql:
            log.info("Adding column ai_mode...")
            await conn.execute(text("""
                ALTER TABLE user_settings 
                ADD COLUMN ai_mode BOOLEAN DEFAULT FALSE
            """))
        
        # Добавляем колонку hybrid_mode, если её нет
        if 'hybrid_mode' not in table_sql:
            log.info("Adding column hybrid_mode...")
            await conn.execute(text("""
                ALTER TABLE user_settings 
                ADD COLUMN hybrid_mode BOOLEAN DEFAULT FALSE
            """))
    
    log.info("Migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(migrate())