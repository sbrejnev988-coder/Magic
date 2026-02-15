#!/usr/bin/env python3
"""
Скрипт миграции для добавления полей оплаты в таблицу orders.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import settings
from bot.database.engine import create_engine, get_session_maker
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def migrate():

    engine = create_engine(settings.database.url)
    session_maker = get_session_maker(engine)
    
    async with engine.begin() as conn:
        # Проверяем существование таблицы и её колонок
        result = await conn.execute(text("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='orders'
        """))
        table_sql = result.scalar()
        if not table_sql:
            log.error("Table 'orders' does not exist.")
            return
        
        log.info(f"Table schema: {table_sql}")
        
        # Добавляем колонку is_paid, если её нет
        if 'is_paid' not in table_sql:
            log.info("Adding column is_paid...")
            await conn.execute(text("""
                ALTER TABLE orders 
                ADD COLUMN is_paid BOOLEAN DEFAULT FALSE
            """))
        
        # Добавляем колонку payment_screenshot, если её нет
        if 'payment_screenshot' not in table_sql:
            log.info("Adding column payment_screenshot...")
            await conn.execute(text("""
                ALTER TABLE orders 
                ADD COLUMN payment_screenshot VARCHAR(500)
            """))
        
        # Добавляем колонку admin_notes, если её нет
        if 'admin_notes' not in table_sql:
            log.info("Adding column admin_notes...")
            await conn.execute(text("""
                ALTER TABLE orders 
                ADD COLUMN admin_notes TEXT
            """))
    
    log.info("Migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(migrate())