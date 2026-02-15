"""
MysticBot — точка входа
"""
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database.engine import create_engine, get_session_maker
from bot.models.base import Base
import bot.models  # регистрация всех моделей в Base.metadata

from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.auth import AuthMiddleware

# === Роутеры (порядок = приоритет!) ===
from bot.handlers.ai_mode import router as ai_mode_router          # FSM — ПЕРВЫЙ
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
from bot.handlers.astrology import router as astrology_router
from bot.handlers.meditation import router as meditation_router
from bot.handlers.history import router as history_router
from bot.handlers.orders import router as orders_router
from bot.handlers.file_upload import router as file_upload_router
from bot.handlers.settings import router as settings_router
from bot.handlers.heartbeat import router as heartbeat_router
from bot.handlers.predictions import router as predictions_router
from bot.services.llm import get_llm_service


def setup_logging(level: str):
    """Настройка логирования."""
    from bot.logging_config import setup_logging as setup_logging_new
    import os
    import logging
    log_json = os.getenv("LOG_JSON", "false").strip().lower() == "true"
    log_file = os.getenv("LOG_FILE", "logs/bot.log")
    setup_logging_new(log_level=level, log_json=log_json, log_file=log_file)
    # Установить уровни для шумных библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    """Основная функция запуска."""
    setup_logging(settings.log_level)
    log = logging.getLogger("main")

    log.info("=" * 60)
    log.info("ЗАПУСК MYSTICBOT")
    log.info("=" * 60)

    # --- Проверка критичных настроек ---
    if not settings.telegram.bot_token:
        log.critical("BOT_TOKEN не задан!")
        return

    # --- LLM-провайдеры ---
    providers = settings.llm_providers_order
    if providers:
        log.info(f"🤖 LLM провайдеры: {' → '.join(p.upper() for p in providers)}")
    else:
        log.warning("⚠️ Ни один LLM-провайдер не настроен!")

    # --- База данных ---
    db_engine = None
    session_maker = None
    try:
        db_engine = create_engine(settings.database.url)
        session_maker = get_session_maker(db_engine)
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("✅ База данных подключена")
    except Exception as e:
        log.error(f"❌ Не удалось подключиться к БД: {e}")
        db_engine = None

    # --- FSM Storage (Redis → Memory fallback) ---
    fsm_storage = None
    try:
        from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
        redis_url = getattr(settings, "redis_url", None) or "redis://localhost:6379/0"
        fsm_storage = RedisStorage.from_url(
            redis_url,
            key_builder=DefaultKeyBuilder(prefix="fsm", with_bot_id=True),
        )
        log.info("✅ Redis FSM storage подключен")
    except Exception as e:
        log.warning(
            f"⚠️ Redis недоступен: {e}. "
            f"Использую MemoryStorage (FSM-данные потеряются при рестарте!)"
        )
        fsm_storage = MemoryStorage()

    # --- Бот и диспетчер ---
    bot = Bot(token=settings.telegram.bot_token)
    dp = Dispatcher(storage=fsm_storage)

    # --- Shutdown hooks (корректное завершение) ---
    async def on_shutdown():
        log.info("🔄 Завершение работы...")
        # Закрытие LLM-клиентов
        try:
            llm = get_llm_service()
            await llm.close()
            log.info("🔒 LLM-клиенты закрыты")
        except Exception as e:
            log.error(f"Ошибка закрытия LLM: {e}")
        # Закрытие пула БД
        if db_engine:
            try:
                await db_engine.dispose()
                log.info("🔒 Connection pool БД закрыт")
            except Exception as e:
                log.error(f"Ошибка закрытия БД: {e}")

    dp.shutdown.register(on_shutdown)

    # --- Middleware ---
    dp.message.middleware(ThrottlingMiddleware(
        rate_limit=settings.rate_limit,
        window=settings.rate_window,
    ))
    if session_maker:
        dp.message.middleware(AuthMiddleware(session_maker))
        dp["session_maker"] = session_maker  # DI — доступ из любого handler

    # ─────────────────────────────────────────────
    # РОУТЕРЫ (порядок критичен!)
    # ─────────────────────────────────────────────
    # 1. AI-режим ПЕРВЫМ — FSM state фильтр имеет приоритет
    dp.include_router(ai_mode_router)

    # 2. Главное меню
    dp.include_router(start_router)

    # 3. Модули (условное включение)
    feature_routers = [
        ("tarot", tarot_router, "Таро"),
        ("numerology", numerology_router, "Нумерология"),
        ("horoscope", horoscope_router, "Гороскопы"),
        ("finance_calendar", finance_calendar_router, "Финансовый календарь"),
        ("dream", dream_router, "Сонник"),
        ("runes", runes_router, "Руны"),
        ("random", random_router, "Рандомайзер"),
        ("ask", ask_router, "AI-консультация"),
        ("astrology", astrology_router, "Астрология"),
        ("meditation", meditation_router, "Медитации"),
    ]

    for feature_key, router, name in feature_routers:
        enable_key = f"enable_{feature_key}"
        if getattr(settings.features, enable_key, True):
            dp.include_router(router)
            log.info(f"  ✅ {name}")

    # 4. Служебные
    dp.include_router(profile_router)
    dp.include_router(history_router)
    dp.include_router(orders_router)
    dp.include_router(file_upload_router)
    dp.include_router(settings_router)
    dp.include_router(heartbeat_router)

    # 5. Админка — ПОСЛЕДНЯЯ
    dp.include_router(admin_router)
    dp.include_router(predictions_router)

    # --- Запуск ---
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("✅ Бот запущен. Ожидание сообщений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=False)
    except KeyboardInterrupt:
        print("\nБот остановлен.")
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}")
        raise
    # shutdown_llm_service вызывается через dp.shutdown.register()
    # НЕ нужен второй asyncio.run()!
