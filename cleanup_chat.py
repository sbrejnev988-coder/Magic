#!/usr/bin/env python3
"""
Скрипт для очистки чата админ-бота от старых сообщений "Доступ запрещён".
Запускать только по указанию пользователя.
"""

import asyncio
import logging
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.config import Settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cleanup")


async def cleanup_messages():
    """Удалить сообщения бота с текстом 'Доступ запрещён' в личном чате с консультантом"""
    settings = Settings()
    
    if not settings.ADMIN_BOT_TOKEN:
        log.critical("ADMIN_BOT_TOKEN не задан в .env файле!")
        return
    
    bot = Bot(token=settings.ADMIN_BOT_TOKEN)
    
    # ID чата с консультантом (личный чат бота с пользователем)
    # Для удаления своих сообщений бот может работать только в чатах, где он есть.
    # В личном чате chat_id равен user_id консультанта.
    chat_id = settings.ADMIN_USER_ID
    
    log.info(f"Начинаю очистку чата {chat_id}...")
    
    deleted_count = 0
    error_count = 0
    
    try:
        # Получаем последние 100 сообщений (можно увеличить)
        # Метод get_updates не подходит, нужно использовать get_chat_history.
        # Но у бота нет доступа к истории чата через get_chat_history, если это private chat.
        # Альтернатива: хранить message_id при отправке, но мы этого не делали.
        
        # Вместо этого можно попробовать удалить сообщения по одному, начиная с последнего известного message_id.
        # Это грубый метод, может удалить лишние сообщения.
        
        log.warning("Этот скрипт может удалить не только сообщения 'Доступ запрещён', но и другие сообщения бота.")
        log.warning("Продолжать? (y/n): ")
        answer = input().strip().lower()
        if answer != 'y':
            log.info("Отменено.")
            return
        
        # Диапазон message_id для удаления (примерно последние 50 сообщений)
        # В приватном чате message_id обычно начинаются с 1 и увеличиваются.
        # Мы не знаем точных message_id, поэтому этот метод ненадёжен.
        
        # Лучший способ — ручное удаление через интерфейс Telegram.
        
        log.error("Автоматическое удаление невозможно без хранения message_id. Рекомендуется удалить сообщения вручную.")
        
    except Exception as e:
        log.error(f"Ошибка: {e}")
    finally:
        await bot.session.close()
    
    log.info(f"Готово. Удалено {deleted_count} сообщений, ошибок {error_count}.")


if __name__ == "__main__":
    asyncio.run(cleanup_messages())