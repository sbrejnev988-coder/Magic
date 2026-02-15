#!/usr/bin/env python3
"""
РЎРєСЂРёРїС‚ РјРёРіСЂР°С†РёРё РґР»СЏ РґРѕР±Р°РІР»РµРЅРёСЏ РїРѕР»РµР№ РѕРіСЂР°РЅРёС‡РµРЅРёР№ РР РІ С‚Р°Р±Р»РёС†Сѓ user_settings.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Р”РѕР±Р°РІР»СЏРµРј РєРѕСЂРµРЅСЊ РїСЂРѕРµРєС‚Р° РІ PYTHONPATH
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
        # РџСЂРѕРІРµСЂСЏРµРј СЃСѓС‰РµСЃС‚РІРѕРІР°РЅРёРµ С‚Р°Р±Р»РёС†С‹ Рё РµС‘ РєРѕР»РѕРЅРѕРє
        result = await conn.execute(text("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='user_settings'
        """))
        table_sql = result.scalar()
        if not table_sql:
            log.error("Table 'user_settings' does not exist.")
            return
        
        log.info(f"Table schema: {table_sql}")
        
        # Р”РѕР±Р°РІР»СЏРµРј РєРѕР»РѕРЅРєСѓ daily_ai_requests, РµСЃР»Рё РµС‘ РЅРµС‚
        if 'daily_ai_requests' not in table_sql:
            log.info("Adding column daily_ai_requests...")
            await conn.execute(text("""
                ALTER TABLE user_settings 
                ADD COLUMN daily_ai_requests INTEGER
            """))
            await conn.execute(text("""
                UPDATE user_settings 
                SET daily_ai_requests = 0 
                WHERE daily_ai_requests IS NULL
            """))
        
        # Р”РѕР±Р°РІР»СЏРµРј РєРѕР»РѕРЅРєСѓ last_ai_request_date, РµСЃР»Рё РµС‘ РЅРµС‚
        if 'last_ai_request_date' not in table_sql:
            log.info("Adding column last_ai_request_date...")
            await conn.execute(text("""
                ALTER TABLE user_settings 
                ADD COLUMN last_ai_request_date DATETIME
            """))
            await conn.execute(text("""
                UPDATE user_settings 
                SET last_ai_request_date = created_at 
                WHERE last_ai_request_date IS NULL
            """))
        
        # Р”РѕР±Р°РІР»СЏРµРј РєРѕР»РѕРЅРєСѓ ai_requests_limit, РµСЃР»Рё РµС‘ РЅРµС‚
        if 'ai_requests_limit' not in table_sql:
            log.info("Adding column ai_requests_limit...")
            await conn.execute(text("""
                ALTER TABLE user_settings 
                ADD COLUMN ai_requests_limit INTEGER
            """))
            await conn.execute(text("""
                UPDATE user_settings 
                SET ai_requests_limit = 15 
                WHERE ai_requests_limit IS NULL
            """))
    
    log.info("Migration completed successfully.")


if __name__ == "__main__":
    asyncio.run(migrate())
