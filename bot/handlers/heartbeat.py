"""
Heartbeat handler для проверки состояния бота.
"""

import logging
import psutil
import os
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()
log = logging.getLogger(__name__)


@router.message(Command("heartbeat"))
async def cmd_heartbeat(message: Message):
    """Проверка состояния бота."""
    try:
        # Основная информация
        pid = os.getpid()
        process = psutil.Process(pid)
        
        # Время работы процесса
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time
        
        # Использование памяти
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        # CPU использование
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # Статистика базы данных (опционально)
        # Можно добавить позже
        
        response = (
            "💓 *Heartbeat MysticBot*\n\n"
            f"*Статус:* ✅ Активен\n"
            f"*PID:* {pid}\n"
            f"*Запущен:* {create_time.strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"*Аптайм:* {uptime.days}д {uptime.seconds // 3600}ч {(uptime.seconds % 3600) // 60}м\n"
            f"*Память:* {memory_mb:.1f} MB\n"
            f"*CPU:* {cpu_percent:.1f}%\n"
            f"*Пользователь:* {message.from_user.full_name} (ID: {message.from_user.id})\n\n"
            "_Бот работает в штатном режиме._"
        )
        
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        log.error(f"Ошибка heartbeat: {e}")
        await message.answer(
            "⚠️ *Heartbeat проверка не удалась*\n"
            "Технические проблемы. Бот всё ещё работает.",
            parse_mode="Markdown"
        )