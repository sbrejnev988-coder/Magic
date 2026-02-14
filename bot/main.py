"""
MysticBot — точка входа
"""

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from bot.config import Settings
from bot.database.engine import create_engine, get_session_maker
from bot.models.base import Base
import bot.models  # регистрация всех моделей в Base.metadata
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
    """Настройка логирования"""
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
    """Основная функция запуска"""
    settings = Settings()
    setup_logging(settings.LOG_LEVEL)
    log = logging.getLogger("main")

    log.info("=" * 60)
    log.info("ЗАПУСК MYSTICBOT")
    log.info("=" * 60)

    if not settings.BOT_TOKEN:
        log.critical("BOT_TOKEN не задан!")
        return

    # Проверка конфигурации
    if not settings.is_database_configured:
        log.warning("База данных не настроена. Некоторые функции будут ограничены.")

    # Инициализация базы данных
    db_engine = None
    session_maker = None
    if settings.is_database_configured:
        try:
            db_engine = create_engine(settings.DATABASE_URL)
            session_maker = get_session_maker(db_engine)
            
            # Создание таблиц, если их нет
            async with db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            log.info("✅ База данных подключена")
        except Exception as e:
            log.error("❌ Не удалось подключиться к базе данных: %s", e)
            db_engine = None

    # Redis FSM storage
    fsm_storage = None
    try:
        fsm_storage = RedisStorage.from_url(
            settings.REDIS_URL,
            key_builder=DefaultKeyBuilder(prefix="fsm", with_bot_id=True)
        )
        log.info("✅ Redis FSM storage подключен")
    except Exception as e:
        log.warning("⚠️ Redis недоступен: %s. Использую memory storage.", e)
        from aiogram.fsm.storage.memory import MemoryStorage
        fsm_storage = MemoryStorage()

    # Бот и диспетчер
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=fsm_storage)

    # Middleware
    dp.message.middleware(ThrottlingMiddleware(rate_limit=settings.RATE_LIMIT, window=settings.RATE_WINDOW))
    dp.message.middleware(AuthMiddleware(session_maker))

    # Роутеры
    dp.include_router(start_router)
    
    if settings.ENABLE_TAROT:
        dp.include_router(tarot_router)
        log.info("✅ Модуль Таро активирован")
    
    if settings.ENABLE_NUMEROLOGY:
        dp.include_router(numerology_router)
        log.info("✅ Нумерология активирована")
    
    if settings.ENABLE_HOROSCOPE:
        dp.include_router(horoscope_router)
        log.info("✅ Гороскопы активированы")
    
    if settings.ENABLE_FINANCE_CALENDAR:
        dp.include_router(finance_calendar_router)
        log.info("✅ Финансовый календарь активирован")
    
    if settings.ENABLE_DREAM:
        dp.include_router(dream_router)
        log.info("✅ Сонник активирован")
    
    if settings.ENABLE_RUNES:
        dp.include_router(runes_router)
        log.info("✅ Руны активированы")
    
    if settings.ENABLE_RANDOM:
        dp.include_router(random_router)
        log.info("✅ Рандомайзер активирован")
    
    if settings.ENABLE_ASK:
        dp.include_router(ask_router)
        log.info("✅ Консультация с AI активирована")
    
    if settings.ENABLE_ASTROLOGY:
        dp.include_router(astrology_router)
        log.info("✅ Астрология активирована")
    
    if settings.ENABLE_MEDITATION:
        dp.include_router(meditation_router)
        log.info("✅ Медитации активированы")
    
    dp.include_router(profile_router)
    dp.include_router(history_router)
    dp.include_router(orders_router)
    dp.include_router(file_upload_router)
    # dp.include_router(search_router)
    dp.include_router(settings_router)
    dp.include_router(heartbeat_router)
    dp.include_router(admin_router)
    dp.include_router(predictions_router)
    dp.include_router(ai_mode_router)

    # Запуск
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("✅ Бот запущен. Ожидание сообщений...")
    log.info("✅ Polling started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        print("\nБот остановлен.")
    except Exception as e:
        logging.critical("Критическая ошибка: %s", e)
        raise
    finally:
        # Закрытие LLM сервиса
        try:
            asyncio.run(shutdown_llm_service())
        except Exception:
            pass