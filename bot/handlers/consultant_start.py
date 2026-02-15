"""
Обработчики команд /start для бота-консультанта.
Показывает меню консультанта, а не пользовательское меню.
"""

import logging

from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import Settings

router = Router()
settings = Settings()
logging.getLogger(__name__).info(f"Consultant start module loaded. ADMIN_USER_ID={settings.ADMIN_USER_ID}")


def is_consultant(user_id: int) -> bool:
    """Проверка прав консультанта"""
    import logging
    log = logging.getLogger(__name__)
    # Приводим оба значения к int для надёжности
    user_id_int = int(user_id)
    admin_id_int = int(settings.ADMIN_USER_ID)
    
    result = user_id_int == admin_id_int
    log.info(f"CONSULTANT_START: Проверка прав: user_id={user_id_int}, ADMIN_USER_ID={admin_id_int}, результат={result}")
    return result


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start для консультанта"""
    if not is_consultant(message.from_user.id):
        await message.answer("⛔️ У вас нет прав доступа к этому боту.")
        return
    
    logging.info(f"Consultant /start from {message.from_user.id}")
    
    # Создаем меню с inline-кнопками
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="📋 Консультации", callback_data="consultant_consultations"),
        types.InlineKeyboardButton(text="💰 Заказы", callback_data="consultant_orders")
    )
    builder.row(
        types.InlineKeyboardButton(text="📝 Черновики", callback_data="consultant_drafts"),
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="consultant_stats")
    )
    builder.row(
        types.InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="consultant_search_user")
    )
    
    welcome_text = f"""
👨\u200d💼 *Добро пожаловать, консультант!*

Это бот-коморка для работы с пользователями MysticBot.

*Доступные действия:*

📋 *Консультации* — просмотр истории консультаций всех пользователей
💰 *Заказы* — просмотр заказов и проверка оплаты
📝 *Черновики* — черновики на проверку (гибридный режим)
📊 *Статистика* — статистика по пользователям и запросам
🔍 *Поиск пользователя* — поиск по ID или имени

*Быстрый доступ:*
/consultations — последние консультации
/orders — последние заказы
/drafts — черновики на проверку
/stats — статистика

*Ваш ID:* `{message.from_user.id}`
"""
    
    await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.message(Command("debug"))
async def cmd_debug(message: Message):
    """Отладочная информация"""
    import logging
    log = logging.getLogger(__name__)
    user_id = message.from_user.id
    admin_id = settings.ADMIN_USER_ID
    is_consult = user_id == admin_id
    log.info(f"DEBUG: user_id={user_id}, admin_id={admin_id}, is_consult={is_consult}")
    
    debug_text = f"""
🔧 *Отладочная информация*

*Ваш ID:* `{user_id}`
*ADMIN_USER_ID:* `{admin_id}`
*is_consultant:* `{is_consult}`

*Типы:*
- user_id type: `{type(user_id)}`
- admin_id type: `{type(admin_id)}`

*Проверка равенства:* `{user_id == admin_id}`
"""
    await message.answer(debug_text, parse_mode="Markdown")


@router.message()
async def handle_unknown(message: Message):
    """Обработчик неизвестных сообщений для консультанта (catch-all, должен быть ПОСЛЕДНИМ)"""
    import logging
    log = logging.getLogger(__name__)
    user_id = message.from_user.id
    is_consult = is_consultant(user_id)
    
    log.info(f"HANDLE_UNKNOWN: user_id={user_id}, is_consultant={is_consult}, text='{message.text}'")
    
    if not is_consult:
        log.warning(f"ACCESS DENIED: user_id={user_id} is not consultant")
        await message.answer("⛔️ У вас нет прав доступа к этому боту.")
        return
    
    hint_text = """
🤔 Этот бот предназначен только для работы консультанта.

Используйте меню консультанта или команды:
/consultant — главное меню
/consultations — консультации
/orders — заказы
/drafts — черновики
/stats — статистика
"""
    
    await message.answer(hint_text, parse_mode="Markdown")
