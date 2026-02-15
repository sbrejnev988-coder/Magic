#!/usr/bin/env python3
"""
Обновить время уведомлений пользователя на текущее время + 1 минута.
"""

import asyncio
from datetime import datetime, time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot.database.engine import create_engine, get_session_maker
from bot.services.user_settings import UserSettingsService
from bot.config import Settings


async def update_time(user_id: int):
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    session_maker = get_session_maker(engine)
    
    async with session_maker() as session:
        user_settings = await UserSettingsService.get_or_create(session, user_id)
        
        # Текущее время + 1 минута
        now = datetime.now()
        new_time = time(now.hour, now.minute + 1)
        user_settings.notification_time = new_time
        
        await session.commit()
        print(f"✅ Время уведомлений для пользователя {user_id} изменено на {new_time.strftime('%H:%M')}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    else:
        user_id = 576704037
    
    asyncio.run(update_time(user_id))