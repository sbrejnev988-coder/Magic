"""
MysticBot вЂ” С‚РѕС‡РєР° РІС…РѕРґР°
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from bot.config import Settings
from bot.database.engine import create_engine, get_session_maker
from bot.models.base import Base
import bot.models  # СЂРµРіРёСЃС‚СЂР°С†РёСЏ РІСЃРµС… РјРѕРґРµР»РµР№ РІ Base.metadata
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.auth import AuthMiddleware
from bot.handlers.start import router as start_router
from bot.handlers.tarot import router as tarot_router
from bot.handlers.numerology import router as numerology_router
from bot.handlers.horoscope import router as horoscope_router
from bot.handlers.finance_calendar import router as finance_calendar_router
from bot.handlers.profile import router as profile_router
from bot.handlers.admin import router as admin_router
from bot.handlers.dream import router as dream_router
from bot.handlers.runes import router as runes_router
from bot.handlers.random import router as random_router
from bot.handlers.ask import router as ask_router
from bot.handlers.ai_mode import router as ai_mode_router
from bot.handlers.astrology import router as astrology_router
from bot.handlers.meditation import router as meditation_router
from bot.handlers.history import router as history_router
from bot.handlers.orders import router as orders_router
from bot.handlers.file_upload import router as file_upload_router
# from bot.handlers.search import router as search_router
from bot.handlers.settings import router as settings_router
from bot.handlers.heartbeat import router as heartbeat_router
from bot.handlers.predictions import router as predictions_router
from bot.services.llm import shutdown_llm_service


def setup_logging(level: str):
    """РќР°СЃС‚СЂРѕР№РєР° Р»РѕРіРёСЂРѕРІР°РЅРёСЏ"""
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("logs/bot.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


async def main():
    """РћСЃРЅРѕРІРЅР°СЏ С„СѓРЅРєС†РёСЏ Р·Р°РїСѓСЃРєР°"""
    settings = Settings()
    setup_logging(settings.LOG_LEVEL)
    log = logging.getLogger("main")

    log.info("=" * 60)
    log.info("Р—РђРџРЈРЎРљ MYSTICBOT")
    log.info("=" * 60)

    if not settings.BOT_TOKEN:
        log.critical("BOT_TOKEN РЅРµ Р·Р°РґР°РЅ!")
        return

    # РџСЂРѕРІРµСЂРєР° РєРѕРЅС„РёРіСѓСЂР°С†РёРё
    if not settings.is_database_configured:
        log.warning("Р‘Р°Р·Р° РґР°РЅРЅС‹С… РЅРµ РЅР°СЃС‚СЂРѕРµРЅР°. РќРµРєРѕС‚РѕСЂС‹Рµ С„СѓРЅРєС†РёРё Р±СѓРґСѓС‚ РѕРіСЂР°РЅРёС‡РµРЅС‹.")

    # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ Р±Р°Р·С‹ РґР°РЅРЅС‹С…
    db_engine = None
    session_maker = None
    if settings.is_database_configured:
        try:
            db_engine = create_engine(settings.DATABASE_URL)
            session_maker = get_session_maker(db_engine)
            
            # РЎРѕР·РґР°РЅРёРµ С‚Р°Р±Р»РёС†, РµСЃР»Рё РёС… РЅРµС‚
            async with db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            log.info("вњ… Р‘Р°Р·Р° РґР°РЅРЅС‹С… РїРѕРґРєР»СЋС‡РµРЅР°")
        except Exception as e:
            log.error("вќЊ РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕРґРєР»СЋС‡РёС‚СЊСЃСЏ Рє Р±Р°Р·Рµ РґР°РЅРЅС‹С…: %s", e)
            db_engine = None

    # Redis FSM storage
    fsm_storage = None
    try:
        fsm_storage = RedisStorage.from_url(
            settings.REDIS_URL,
            key_builder=DefaultKeyBuilder(prefix="fsm", with_bot_id=True)
        )
        log.info("вњ… Redis FSM storage РїРѕРґРєР»СЋС‡РµРЅ")
    except Exception as e:
        log.warning("вљ пёЏ Redis РЅРµРґРѕСЃС‚СѓРїРµРЅ: %s. РСЃРїРѕР»СЊР·СѓСЋ memory storage.", e)
        from aiogram.fsm.storage.memory import MemoryStorage
        fsm_storage = MemoryStorage()

    # РћСЃРЅРѕРІРЅРѕР№ Р±Р»РѕРє СЃ graceful shutdown
    try:
        # Р‘РѕС‚ Рё РґРёСЃРїРµС‚С‡РµСЂ
        bot = Bot(token=settings.BOT_TOKEN)
        dp = Dispatcher(storage=fsm_storage)

        # Р РµРіРёСЃС‚СЂР°С†РёСЏ graceful shutdown
        from bot.services.llm import shutdown_llm_service
        dp.shutdown.register(shutdown_llm_service)
        if db_engine:
            dp.shutdown.register(db_engine.dispose)

        # Middleware
        dp.message.middleware(ThrottlingMiddleware(rate_limit=settings.RATE_LIMIT, window=settings.RATE_WINDOW))
        dp.message.middleware(AuthMiddleware(session_maker))

        # Р РѕСѓС‚РµСЂС‹
        dp.include_router(ai_mode_router)
        dp.include_router(start_router)
        
        if settings.ENABLE_TAROT:
            dp.include_router(tarot_router)
            log.info("вњ… РњРѕРґСѓР»СЊ РўР°СЂРѕ Р°РєС‚РёРІРёСЂРѕРІР°РЅ")
        
        if settings.ENABLE_NUMEROLOGY:
            dp.include_router(numerology_router)
            log.info("вњ… РќСѓРјРµСЂРѕР»РѕРіРёСЏ Р°РєС‚РёРІРёСЂРѕРІР°РЅР°")
        
        if settings.ENABLE_HOROSCOPE:
            dp.include_router(horoscope_router)
            log.info("вњ… Р“РѕСЂРѕСЃРєРѕРїС‹ Р°РєС‚РёРІРёСЂРѕРІР°РЅС‹")
        
        if settings.ENABLE_FINANCE_CALENDAR:
            dp.include_router(finance_calendar_router)
            log.info("вњ… Р¤РёРЅР°РЅСЃРѕРІС‹Р№ РєР°Р»РµРЅРґР°СЂСЊ Р°РєС‚РёРІРёСЂРѕРІР°РЅ")
        
        if settings.ENABLE_DREAM:
            dp.include_router(dream_router)
            log.info("вњ… РЎРѕРЅРЅРёРє Р°РєС‚РёРІРёСЂРѕРІР°РЅ")
        
        if settings.ENABLE_RUNES:
            dp.include_router(runes_router)
            log.info("вњ… Р СѓРЅС‹ Р°РєС‚РёРІРёСЂРѕРІР°РЅС‹")
        
        if settings.ENABLE_RANDOM:
            dp.include_router(random_router)
            log.info("вњ… Р Р°РЅРґРѕРјР°Р№Р·РµСЂ Р°РєС‚РёРІРёСЂРѕРІР°РЅ")
        
        if settings.ENABLE_ASK:
            dp.include_router(ask_router)
            log.info("вњ… РљРѕРЅСЃСѓР»СЊС‚Р°С†РёСЏ СЃ AI Р°РєС‚РёРІРёСЂРѕРІР°РЅР°")
        
        if settings.ENABLE_ASTROLOGY:
            dp.include_router(astrology_router)
            log.info("вњ… РђСЃС‚СЂРѕР»РѕРіРёСЏ Р°РєС‚РёРІРёСЂРѕРІР°РЅР°")
        
        if settings.ENABLE_MEDITATION:
            dp.include_router(meditation_router)
            log.info("вњ… РњРµРґРёС‚Р°С†РёРё Р°РєС‚РёРІРёСЂРѕРІР°РЅС‹")
        
        dp.include_router(profile_router)
        dp.include_router(history_router)
        dp.include_router(orders_router)
        dp.include_router(file_upload_router)
        # dp.include_router(search_router)
        dp.include_router(settings_router)
        dp.include_router(heartbeat_router)
        dp.include_router(admin_router)
        dp.include_router(predictions_router)

        # Р—Р°РїСѓСЃРє
        await bot.delete_webhook(drop_pending_updates=True)
        log.info("вњ… Р‘РѕС‚ Р·Р°РїСѓС‰РµРЅ. РћР¶РёРґР°РЅРёРµ СЃРѕРѕР±С‰РµРЅРёР№...")
        log.info("вњ… Polling started")
        await dp.start_polling(bot)
    finally:
        # Graceful shutdown: Р·Р°РєСЂС‹С‚РёРµ СЂРµСЃСѓСЂСЃРѕРІ
        if db_engine:
            try:
                await db_engine.dispose()
                log.info("вњ… Р‘Р°Р·Р° РґР°РЅРЅС‹С… РѕС‚РєР»СЋС‡РµРЅР°")
            except Exception as e:
                log.error(f"РћС€РёР±РєР° РїСЂРё РѕС‚РєР»СЋС‡РµРЅРёРё Р±Р°Р·С‹ РґР°РЅРЅС‹С…: {e}")
        if fsm_storage and hasattr(fsm_storage, 'close'):
            try:
                fsm_storage.close()
                log.info("вњ… Redis FSM storage Р·Р°РєСЂС‹С‚")
            except Exception as e:
                log.error(f"РћС€РёР±РєР° РїСЂРё Р·Р°РєСЂС‹С‚РёРё Redis storage: {e}")
        log.info("вњ… Р РµСЃСѓСЂСЃС‹ РѕСЃРІРѕР±РѕР¶РґРµРЅС‹")


if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=False)
    except KeyboardInterrupt:
        print("\nР‘РѕС‚ РѕСЃС‚Р°РЅРѕРІР»РµРЅ.")
    except Exception as e:
        logging.critical("РљСЂРёС‚РёС‡РµСЃРєР°СЏ РѕС€РёР±РєР°: %s", e)
        raise