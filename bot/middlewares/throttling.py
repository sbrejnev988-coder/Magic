"""
Middleware для ограничения частоты запросов (rate limiting)
"""

import logging
import time
from typing import Callable, Dict, Any, Awaitable
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message

log = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Ограничение количества сообщений от пользователя за период времени"""

    def __init__(self, rate_limit: int = 30, window: int = 60):
        self.rate_limit = rate_limit  # Максимальное количество сообщений
        self.window = window  # Окно времени в секундах
        self.user_timestamps = defaultdict(list)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # Очистка каждые 5 минут
        super().__init__()

    def _cleanup_old_entries(self, current_time: float):
        """Периодическая очистка старых записей для предотвращения утечки памяти"""
        if current_time - self.last_cleanup > self.cleanup_interval:
            users_to_remove = []
            for user_id, timestamps in self.user_timestamps.items():
                # Удаляем старые метки
                self.user_timestamps[user_id] = [
                    ts for ts in timestamps if current_time - ts < self.window
                ]
                # Если у пользователя не осталось меток, удаляем его из словаря
                if not self.user_timestamps[user_id]:
                    users_to_remove.append(user_id)
            
            for user_id in users_to_remove:
                del self.user_timestamps[user_id]
            
            self.last_cleanup = current_time
            if users_to_remove:
                log.debug(f"Throttling: очищено {len(users_to_remove)} неактивных пользователей")

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        log.debug(f"Throttling middleware: user {user_id}, message length: {len(event.text or '')}")
        current_time = time.time()

        # Периодическая очистка памяти
        self._cleanup_old_entries(current_time)

        # Очистка старых временных меток для текущего пользователя
        self.user_timestamps[user_id] = [
            ts for ts in self.user_timestamps[user_id]
            if current_time - ts < self.window
        ]

        # Проверка лимита
        if len(self.user_timestamps[user_id]) >= self.rate_limit:
            remaining_time = int(self.window - (current_time - self.user_timestamps[user_id][0]))
            await event.answer(
                f"⚠️ Слишком много запросов. Пожалуйста, подождите {remaining_time} секунд."
            )
            return

        # Добавление новой временной метки
        self.user_timestamps[user_id].append(current_time)

        # Вызов следующего обработчика
        return await handler(event, data)