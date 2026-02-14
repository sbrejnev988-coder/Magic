#!/usr/bin/env python3
"""
РЎРєСЂРёРїС‚ РґР»СЏ РѕС‚РїСЂР°РІРєРё РµР¶РµРґРЅРµРІРЅС‹С… СѓРІРµРґРѕРјР»РµРЅРёР№ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРј MysticBot.
Р—Р°РїСѓСЃРєР°РµС‚СЃСЏ РїРѕ cron (РєР°Р¶РґС‹Рµ 5 РјРёРЅСѓС‚) Рё РѕС‚РїСЂР°РІР»СЏРµС‚ СѓРІРµРґРѕРјР»РµРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРј,
Сѓ РєРѕС‚РѕСЂС‹С… РІРєР»СЋС‡РµРЅС‹ РµР¶РµРґРЅРµРІРЅС‹Рµ СѓРІРµРґРѕРјР»РµРЅРёСЏ РЅР° С‚РµРєСѓС‰РµРµ РІСЂРµРјСЏ.
"""

import asyncio
import logging
import sys
from datetime import datetime, time
from pathlib import Path

# Р”РѕР±Р°РІР»СЏРµРј РїСѓС‚СЊ Рє РїСЂРѕРµРєС‚Сѓ
sys.path.insert(0, str(Path(__file__).parent))

from bot.database.engine import create_engine, get_session_maker
from bot.services.user_settings import UserSettingsService
from bot.services.daily_content import DailyContentService
from bot.config import Settings

# Telegram Bot
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramAPIError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/cron.log", encoding="utf-8")
    ]
)
log = logging.getLogger("cron_notifications")


class TelegramSender:
    """РћС‚РїСЂР°РІС‰РёРє СЃРѕРѕР±С‰РµРЅРёР№ С‡РµСЂРµР· Telegram Bot API."""
    
    def __init__(self, token: str):
        self.bot = Bot(token=token, default=DefaultBotProperties(parse_mode="Markdown"))
    
    async def send_message(self, user_id: int, text: str) -> bool:
        """РћС‚РїСЂР°РІРёС‚СЊ СЃРѕРѕР±С‰РµРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ."""
        try:
            await self.bot.send_message(chat_id=user_id, text=text)
            log.debug(f"РЎРѕРѕР±С‰РµРЅРёРµ РѕС‚РїСЂР°РІР»РµРЅРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ {user_id}")
            return True
        except TelegramAPIError as e:
            log.error(f"РћС€РёР±РєР° Telegram API РґР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_id}: {e}")
            return False
        except Exception as e:
            log.error(f"РќРµРёР·РІРµСЃС‚РЅР°СЏ РѕС€РёР±РєР° РїСЂРё РѕС‚РїСЂР°РІРєРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ {user_id}: {e}")
            return False
    
    async def close(self):
        """Р—Р°РєСЂС‹С‚СЊ СЃРµСЃСЃРёСЋ Р±РѕС‚Р°."""
        await self.bot.session.close()


async def send_notification_to_user(user_id: int, settings, sender: TelegramSender) -> bool:
    """
    РћС‚РїСЂР°РІРёС‚СЊ СѓРІРµРґРѕРјР»РµРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ.
    Р’РѕР·РІСЂР°С‰Р°РµС‚ True РµСЃР»Рё РѕС‚РїСЂР°РІР»РµРЅРѕ СѓСЃРїРµС€РЅРѕ, False РІ СЃР»СѓС‡Р°Рµ РѕС€РёР±РєРё.
    """
    # Р“РµРЅРµСЂРёСЂСѓРµРј СѓРІРµРґРѕРјР»РµРЅРёРµ РЅР° РѕСЃРЅРѕРІРµ РЅР°СЃС‚СЂРѕРµРє
    try:
        notification_text = DailyContentService.generate_daily_notification(
            user_id=user_id,
            include_rune=settings.notify_rune_of_day,
            include_affirmation=settings.notify_affirmation_of_day,
            include_tarot=settings.notify_tarot_card_of_day,
            include_zodiac=settings.notify_horoscope_daily,
            include_meditation=settings.notify_meditation_reminder,
        )
        
        log.info(f"рџ“Ё РћС‚РїСЂР°РІРєР° СѓРІРµРґРѕРјР»РµРЅРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ {user_id}")
        success = await sender.send_message(user_id, notification_text)
        
        if success:
            log.info(f"вњ… РЈРІРµРґРѕРјР»РµРЅРёРµ РѕС‚РїСЂР°РІР»РµРЅРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ {user_id}")
        else:
            log.warning(f"вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ СѓРІРµРґРѕРјР»РµРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ {user_id}")
        
        return success
        
    except Exception as e:
        log.error(f"РћС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё СѓРІРµРґРѕРјР»РµРЅРёСЏ РґР»СЏ {user_id}: {e}")
        return False


async def process_daily_notifications():
    """РћСЃРЅРѕРІРЅР°СЏ С„СѓРЅРєС†РёСЏ РѕР±СЂР°Р±РѕС‚РєРё СѓРІРµРґРѕРјР»РµРЅРёР№."""
    log.info("рџ”„ Р—Р°РїСѓСЃРє РїСЂРѕРІРµСЂРєРё РµР¶РµРґРЅРµРІРЅС‹С… СѓРІРµРґРѕРјР»РµРЅРёР№")
    
    settings = Settings()
    engine = create_engine(settings.DATABASE_URL)
    session_maker = get_session_maker(engine)
    sender = TelegramSender(settings.BOT_TOKEN)
    
    current_time = datetime.now().time()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    log.info(f"вЏ° РўРµРєСѓС‰РµРµ РІСЂРµРјСЏ: {current_hour:02d}:{current_minute:02d}")
    
    try:
        async with session_maker() as session:
            # РџРѕР»СѓС‡Р°РµРј РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№ СЃ РІРєР»СЋС‡РµРЅРЅС‹РјРё СѓРІРµРґРѕРјР»РµРЅРёСЏРјРё РЅР° С‚РµРєСѓС‰РµРµ РІСЂРµРјСЏ
            users = await UserSettingsService.get_users_with_daily_notifications(
                session, current_hour, current_minute
            )
            
            log.info(f"рџ‘¤ РќР°Р№РґРµРЅРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№ РґР»СЏ СѓРІРµРґРѕРјР»РµРЅРёР№: {len(users)}")
            
            sent_count = 0
            error_count = 0
            
            for user_settings in users:
                log.debug(f"РћР±СЂР°Р±РѕС‚РєР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ {user_settings.user_id}")
                success = await send_notification_to_user(
                    user_settings.user_id, 
                    user_settings, 
                    sender
                )
                if success:
                    sent_count += 1
                else:
                    error_count += 1
                
                # РќРµР±РѕР»СЊС€Р°СЏ Р·Р°РґРµСЂР¶РєР° РјРµР¶РґСѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏРјРё
                await asyncio.sleep(0.3)
        
        log.info(f"вњ… РЈРІРµРґРѕРјР»РµРЅРёСЏ РѕС‚РїСЂР°РІР»РµРЅС‹: {sent_count}, РѕС€РёР±РѕРє: {error_count}")
        
        if sent_count == 0 and error_count == 0:
            log.info("в„№пёЏ РќРµС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№ РґР»СЏ СѓРІРµРґРѕРјР»РµРЅРёР№ РІ СЌС‚Рѕ РІСЂРµРјСЏ.")
    
    finally:
        await sender.close()


if __name__ == "__main__":
    try:
        asyncio.run(process_daily_notifications())
    except KeyboardInterrupt:
        log.info("РЎРєСЂРёРїС‚ РѕСЃС‚Р°РЅРѕРІР»РµРЅ")
    except Exception as e:
        log.critical(f"РљСЂРёС‚РёС‡РµСЃРєР°СЏ РѕС€РёР±РєР°: {e}", exc_info=True)
        sys.exit(1)
