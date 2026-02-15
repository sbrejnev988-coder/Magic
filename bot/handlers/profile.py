"""
Обработчики профиля пользователя
"""

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Показать профиль пользователя"""
    user = message.from_user
    profile_text = f"""
👤 *Ваш профиль*

*ID:* {user.id}
*Имя:* {user.first_name}
*Фамилия:* {user.last_name or '—'}
*Username:* @{user.username or '—'}

*Статистика:*
- Раскладов Таро: 0
- Нумерологических расчётов: 0
- Гороскопов получено: 0

*Подписка:* Базовая (бесплатная)
"""
    await message.answer(profile_text, parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика использования бота"""
    stats_text = """
📊 *Статистика MysticBot*

*Всего пользователей:* 1
*Активных сегодня:* 1
*Всего раскладов:* 0
*Средняя оценка:* 5.0

*Популярные разделы:*
1. Карты Таро
2. Гороскопы
3. Нумерология
"""
    await message.answer(stats_text, parse_mode="Markdown")