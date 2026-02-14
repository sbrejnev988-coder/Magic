"""
Middleware для авторизации и проверки подписки
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

log = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Проверка доступа пользователя к платным функциям"""

    def __init__(self, session_maker=None):
        self.session_maker = session_maker
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Базовые данные пользователя
        user_id = event.from_user.id
        username = event.from_user.username
        log.info(f"Auth middleware: user {user_id}, message: {event.text}")
        
        # Здесь можно добавить проверку подписки в базе данных
        # если session_maker передан
        is_premium = False  # По умолчанию бесплатный доступ
        
        if self.session_maker:
            # Проверка подписки в БД
            try:
                async with self.session_maker() as session:
                    # Заглушка - нужно реализовать запрос к таблице подписок
                    pass
            except Exception as e:
                log.error("Ошибка при проверке подписки: %s", e)
        
        # Сохраняем информацию о подписке в data для использования в хендлерах
        data["is_premium"] = is_premium
        data["session_maker"] = self.session_maker
        
        # Пропускаем запрос дальше
        return await handler(event, data)