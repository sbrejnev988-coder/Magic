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
    """Ограничение частоты сообщений от пользователя.

    rate_limit: минимальный интервал между сообщениями в секундах (float, напр. 0.5)
    window: окно времени для подсчёта в секундах
    """

    def __init__(self, rate_limit: float = 0.5, window: int = 1):
        self.rate_limit = rate_limit  # Минимальный интервал между сообщениями (сек)
        self.window = window  # Окно времени в секундах
        self.user_timestamps: dict[int, list[float]] = defaultdict(list)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # Очистка каждые 5 минут
        super().__init__()

    def _cleanup_old_entries(self, current_time: float):
        """Периодическая очистка старых записей для предотвращения утечки памяти"""
        if current_time - self.last_cleanup > self.cleanup_interval:
            users_to_remove = []
            for user_id, timestamps in self.user_timestamps.items():
                self.user_timestamps[user_id] = [
                    ts for ts in timestamps if current_time - ts < self.window
                ]
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

        # Проверка минимального интервала между сообщениями
        timestamps = self.user_timestamps[user_id]
        if timestamps:
            last_message_time = timestamps[-1]
            elapsed = current_time - last_message_time
            if elapsed < self.rate_limit:
                remaining = self.rate_limit - elapsed
                await event.answer(
                    f"⚠️ Слишком частые запросы. Подождите {remaining:.1f} сек."
                )
                return

        # Очистка старых временных меток
        self.user_timestamps[user_id] = [
            ts for ts in timestamps if current_time - ts < self.window
        ]

        # Добавление новой временной метки
        self.user_timestamps[user_id].append(current_time)

        # Вызов следующего обработчика
        return await handler(event, data)
