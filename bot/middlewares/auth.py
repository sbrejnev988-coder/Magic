"""
Middleware РґР»СЏ Р°РІС‚РѕСЂРёР·Р°С†РёРё Рё РїСЂРѕРІРµСЂРєРё РїРѕРґРїРёСЃРєРё
"""

import logging
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

log = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """РџСЂРѕРІРµСЂРєР° РґРѕСЃС‚СѓРїР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ Рє РїР»Р°С‚РЅС‹Рј С„СѓРЅРєС†РёСЏРј"""

    def __init__(self, session_maker=None):
        self.session_maker = session_maker
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Р‘Р°Р·РѕРІС‹Рµ РґР°РЅРЅС‹Рµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
        user_id = event.from_user.id
        username = event.from_user.username
        log.debug(f"Auth middleware: user {user_id} (@{username}), message length: {len(event.text or '')}")
        
        # Р—РґРµСЃСЊ РјРѕР¶РЅРѕ РґРѕР±Р°РІРёС‚СЊ РїСЂРѕРІРµСЂРєСѓ РїРѕРґРїРёСЃРєРё РІ Р±Р°Р·Рµ РґР°РЅРЅС‹С…
        # РµСЃР»Рё session_maker РїРµСЂРµРґР°РЅ
        is_premium = False  # РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ Р±РµСЃРїР»Р°С‚РЅС‹Р№ РґРѕСЃС‚СѓРї
        
        if self.session_maker:
            # РџСЂРѕРІРµСЂРєР° РїРѕРґРїРёСЃРєРё РІ Р‘Р”
            try:
                async with self.session_maker() as session:
                    # Р—Р°РіР»СѓС€РєР° - РЅСѓР¶РЅРѕ СЂРµР°Р»РёР·РѕРІР°С‚СЊ Р·Р°РїСЂРѕСЃ Рє С‚Р°Р±Р»РёС†Рµ РїРѕРґРїРёСЃРѕРє
                    pass
            except Exception as e:
                log.error("РћС€РёР±РєР° РїСЂРё РїСЂРѕРІРµСЂРєРµ РїРѕРґРїРёСЃРєРё: %s", e)
        
        # РЎРѕС…СЂР°РЅСЏРµРј РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ РїРѕРґРїРёСЃРєРµ РІ data РґР»СЏ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ РІ С…РµРЅРґР»РµСЂР°С…
        data["is_premium"] = is_premium
        data["session_maker"] = self.session_maker
        
        # РџСЂРѕРїСѓСЃРєР°РµРј Р·Р°РїСЂРѕСЃ РґР°Р»СЊС€Рµ
        return await handler(event, data)