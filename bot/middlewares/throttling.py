"""
Middleware для ограничения частоты запросов (rate limiting)
"""

import logging
import time
from typing import Callable, Dict, Any, Awaitable
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottlingMiddleware(BaseMiddleware):
    """Ограничение количества сообщений от пользователя за период времени"""

    def __init__(self, rate_limit: int = 30, window: int = 60):
        self.rate_limit = rate_limit  # Максимальное количество сообщений
        self.window = window  # Окно времени в секундах
        self.user_timestamps = defaultdict(list)
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        logging.info(f"Throttling middleware: message from {user_id}: {event.text}")
        current_time = time.time()

        # Очистка старых временных меток
        self.user_timestamps[user_id] = [
            ts for ts in self.user_timestamps[user_id]
            if current_time - ts < self.window
        ]

        # Проверка лимита
        if len(self.user_timestamps[user_id]) >= self.rate_limit:
            await event.answer(
                f"⚠️ Слишком много запросов. Пожалуйста, подождите {self.window} секунд."
            )
            return

        # Добавление новой временной метки
        self.user_timestamps[user_id].append(current_time)

        # Вызов следующего обработчика
        return await handler(event, data)