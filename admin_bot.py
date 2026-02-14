"""
Бот-коморка для консультанта - просмотр истории консультаций, чеков платежей, черновиков.
Использует токен админ-бота, предназначен только для консультанта.
"""

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from bot.config import Settings
from bot.database.engine import create_engine, get_session_maker
from bot.models.base import Base
import bot.models  # регистрация всех моделей в Base.metadata
from bot.middlewares.auth import AuthMiddleware
from bot.handlers.consultant import router as consultant_router
# from bot.handlers.orders import router as orders_router  # не нужен для консультанта
from bot.handlers.consultant_start import router as consultant_start_router  # для /start в админ-боте
from bot.handlers.admin import router as admin_router  # админ-панель для администратора
from bot.handlers.admin_search import router as admin_search_router  # расширенный поиск пользователей


def setup_logging(level: str):
    """Настройка логирования"""
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("logs/admin_bot.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


async def set_consultant_commands(bot: Bot):
    """Устанавливает команды меню для консультант-бота"""
    log = logging.getLogger("admin_bot")
    try:
        commands = [
            types.BotCommand(command="start", description="Главное меню консультанта"),
            types.BotCommand(command="consultant", description="Главное меню консультанта"),
            types.BotCommand(command="consultations", description="История консультаций"),
            types.BotCommand(command="orders", description="Заказы пользователей"),
            types.BotCommand(command="drafts", description="Черновики на проверке"),
            types.BotCommand(command="stats", description="Статистика"),
            types.BotCommand(command="search", description="Расширенный поиск пользователей"),
            types.BotCommand(command="user", description="Детальный профиль пользователя"),
            types.BotCommand(command="debug", description="Отладочная информация"),
        ]
        log.info(f"Устанавливаю {len(commands)} команд...")
        await bot.set_my_commands(commands)
        log.info("✅ Команды консультанта установлены")
    except Exception as e:
        log.error(f"❌ Ошибка установки команд: {e}", exc_info=True)


async def main():
    """Запуск админ-бота"""
    setup_logging("DEBUG")
    log = logging.getLogger("admin_bot")
    
    log.info("=" * 60)
    log.info("ЗАПУСК АДМИН-БОТА")
    log.info("=" * 60)
    
    # Загружаем конфигурацию
    settings = Settings()
    
    if not settings.ADMIN_BOT_TOKEN:
        log.critical("ADMIN_BOT_TOKEN не задан в .env файле!")
        return
    
    log.info(f"Токен админ-бота: {settings.ADMIN_BOT_TOKEN[:10]}...")
    log.info(f"ID администратора: {settings.ADMIN_USER_ID}")
    
    # Подключаем базу данных
    engine = create_engine(settings.DATABASE_URL)
    session_maker = get_session_maker(engine)
    
    # Создаём таблицы, если их нет
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    log.info("✅ База данных подключена")
    
    # Настройка FSM хранилища
    if settings.REDIS_URL:
        try:
            from redis.asyncio import Redis
            redis = Redis.from_url(settings.REDIS_URL)
            fsm_storage = RedisStorage(redis, key_builder=DefaultKeyBuilder(with_bot_id=True))
            log.info("✅ Redis подключён для FSM")
        except Exception as e:
            log.warning("⚠️ Redis недоступен: %s. Использую memory storage.", e)
            from aiogram.fsm.storage.memory import MemoryStorage
            fsm_storage = MemoryStorage()
    else:
        from aiogram.fsm.storage.memory import MemoryStorage
        fsm_storage = MemoryStorage()
    
    # Бот и диспетчер
    bot = Bot(token=settings.ADMIN_BOT_TOKEN)
    dp = Dispatcher(storage=fsm_storage)
    
    # Middleware
    dp.message.middleware(AuthMiddleware(session_maker))
    
    # Включаем роутеры для консультанта
    dp.include_router(consultant_start_router)  # для /start (специальный для консультанта)
    dp.include_router(consultant_router)
    dp.include_router(admin_router)  # админ-панель для администратора
    dp.include_router(admin_search_router)  # расширенный поиск пользователей
    # orders_router не включаем - это для пользовательских заказов
    
    # Запуск
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Устанавливаю команды консультанта...")
    await set_consultant_commands(bot)
    log.info("✅ Админ-бот запущен. Ожидание сообщений...")
    log.info("✅ Polling started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=True)
    except KeyboardInterrupt:
        print("\nАдмин-бот остановлен.")
    except Exception as e:
        logging.critical("Критическая ошибка: %s", e)
        raise