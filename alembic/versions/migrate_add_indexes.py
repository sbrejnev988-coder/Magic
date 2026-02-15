#!/usr/bin/env python3
"""
Добавление индексов для улучшения производительности БД.
Запускать один раз после создания таблиц.
"""

import asyncio
import logging
from sqlalchemy import text
from bot.database.engine import create_engine
from bot.config import Settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


async def add_indexes():
    """Добавляет индексы к существующим таблицам"""
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    
    indexes = [
        # user_settings
        ("user_settings", "user_id", "idx_user_settings_user_id"),
        # orders
        ("orders", "user_id", "idx_orders_user_id"),
        ("orders", "created_at", "idx_orders_created_at"),
        ("orders", "status", "idx_orders_status"),
        # consultations
        ("consultations", "user_id", "idx_consultations_user_id"),
        ("consultations", "created_at", "idx_consultations_created_at"),
        # hybrid_drafts
        ("hybrid_drafts", "user_id", "idx_hybrid_drafts_user_id"),
        ("hybrid_drafts", "status", "idx_hybrid_drafts_status"),
        ("hybrid_drafts", "created_at", "idx_hybrid_drafts_created_at"),
        # prediction_history
        ("prediction_history", "user_id", "idx_prediction_history_user_id"),
        ("prediction_history", "prediction_type", "idx_prediction_history_type"),
        ("prediction_history", "created_at", "idx_prediction_history_created_at"),
    ]
    
    async with engine.begin() as conn:
        for table, column, idx_name in indexes:
            try:
                # Проверяем, существует ли уже индекс
                check_sql = text(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name='{idx_name}' AND tbl_name='{table}'
                """)
                result = await conn.execute(check_sql)
                existing = result.fetchone()
                
                if existing:
                    log.info(f"Индекс {idx_name} уже существует, пропускаем")
                    continue
                
                # Создаём индекс
                create_sql = text(f"CREATE INDEX {idx_name} ON {table} ({column})")
                await conn.execute(create_sql)
                log.info(f"✅ Создан индекс {idx_name} на {table}.{column}")
                
            except Exception as e:
                log.error(f"❌ Ошибка создания индекса {idx_name}: {e}")
    
    log.info("✅ Все индексы добавлены (или уже существуют)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(add_indexes())