#!/usr/bin/env python3
"""
Р’РєР»СЋС‡РёС‚СЊ РµР¶РµРґРЅРµРІРЅС‹Рµ СѓРІРµРґРѕРјР»РµРЅРёСЏ РґР»СЏ СѓРєР°Р·Р°РЅРЅРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from datetime import time
from bot.database.engine import create_engine, get_session_maker
from bot.services.user_settings import UserSettingsService
from bot.config import Settings


async def enable_notifications(user_id: int):
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    session_maker = get_session_maker(engine)
    
    async with session_maker() as session:
        user_settings = await UserSettingsService.get_or_create(session, user_id)
        
        # Р’РєР»СЋС‡Р°РµРј СѓРІРµРґРѕРјР»РµРЅРёСЏ РЅР° 09:00
        user_settings.enable_daily_notifications = True
        user_settings.notification_time = time(9, 0)  # 09:00
        user_settings.notify_rune_of_day = True
        user_settings.notify_affirmation_of_day = True
        user_settings.notify_horoscope_daily = True
        user_settings.notify_tarot_card_of_day = False
        user_settings.notify_meditation_reminder = True
        
        await session.commit()
        print(f"вњ… РЈРІРµРґРѕРјР»РµРЅРёСЏ РІРєР»СЋС‡РµРЅС‹ РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_id} РЅР° 09:00")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    else:
        user_id = 576704037  # РњР°РєСЃРёРј
    
    asyncio.run(enable_notifications(user_id))
