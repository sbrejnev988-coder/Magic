"""
Расширенный поиск пользователей для админ-панели.
Интеграция с UserSearchService для фильтрации и аналитики.
"""

import logging
from typing import Optional
from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.user_search_service import UserSearchService, search_users_by_criteria, get_user_full_profile
from bot.database.engine import create_engine, get_session_maker
from bot.config import settings
from bot.handlers.consultant import is_consultant

router = Router()
log = logging.getLogger(__name__)

# Создаем engine и session_maker для работы с БД

engine = create_engine(settings.database.url)
session_maker = get_session_maker(engine)


class SearchStates(StatesGroup):
    """Состояния FSM для расширенного поиска"""
    waiting_search_query = State()
    waiting_filters = State()


@router.message(Command("search"))
async def cmd_search(message: Message, command: Optional[CommandObject] = None):
    """Расширенный поиск пользователей"""
    if not is_consultant(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён.")
        return
    
    query = command.args if command and command.args else None
    
    # Создаём меню поиска
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🔍 Быстрый поиск", callback_data="search_quick"),
        types.InlineKeyboardButton(text="🎯 Расширенные фильтры", callback_data="search_filters")
    )
    builder.row(
        types.InlineKeyboardButton(text="📊 Активные пользователи", callback_data="search_active"),
        types.InlineKeyboardButton(text="💰 Платящие пользователи", callback_data="search_paid")
    )
    builder.row(
        types.InlineKeyboardButton(text="📈 Статистика", callback_data="search_stats"),
        types.InlineKeyboardButton(text="🔙 В меню", callback_data="consultant_menu")
    )
    
    help_text = """
🔍 *Расширенный поиск пользователей*

*Команды:*
`/search [запрос]` — быстрый поиск по ID, имени или username
`/search_filters` — поиск с фильтрами
`/search_active` — активные пользователи (7 дней)
`/search_paid` — пользователи с оплаченными заказами
`/search_stats` — общая статистика

*Примеры:*
`/search 576704037` — поиск по ID
`/search Максим` — поиск по имени
`/search @username` — поиск по username
"""
    
    if query:
        # Если есть запрос, сразу выполняем поиск
        await perform_search(message, query)
    else:
        await message.answer(help_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


async def perform_search(message: Message, query: str, page: int = 1, limit: int = 10):
    """Выполняет поиск и отображает результаты"""
    async with session_maker() as session:
        try:
            users, total = await search_users_by_criteria(
                session=session,
                query=query,
                limit=limit,
                offset=(page - 1) * limit
            )
            
            if not users:
                await message.answer(f"❌ По запросу `{query}` ничего не найдено.")
                return
            
            # Формируем ответ
            response = f"🔍 *Результаты поиска: `{query}`*\n"
            response += f"*Найдено пользователей:* {total}\n"
            response += f"*Страница:* {page} из {((total - 1) // limit) + 1}\n\n"
            
            for i, user in enumerate(users, start=1):
                response += f"*{i}. Пользователь ID:* `{user['user_id']}`\n"
                response += f"   *Язык:* {user['preferred_language']}\n"
                response += f"   *Активность:* {user['last_active'][:10] if user['last_active'] else 'нет данных'}\n"
                response += f"   *Консультации:* {user['total_consultations']} | *Заказы:* {user['total_orders']} ({user['paid_orders']} оплач.)\n"
                response += f"   *Предсказания:* {user['total_predictions']} | *Режим ИИ:* {'✅' if user['ai_mode'] else '❌'}\n"
                
                if user.get('last_order'):
                    order = user['last_order']
                    response += f"   *Последний заказ:* #{order['id']} ({order['status']}, {'оплачен' if order['is_paid'] else 'не оплачен'})\n"
                
                response += "   " + "─" * 30 + "\n"
            
            # Создаём клавиатуру пагинации
            builder = InlineKeyboardBuilder()
            if page > 1:
                builder.button(text="◀️ Назад", callback_data=f"search_page:{query}:{page-1}")
            if page < ((total - 1) // limit) + 1:
                builder.button(text="Вперёд ▶️", callback_data=f"search_page:{query}:{page+1}")
            
            builder.button(text="🔍 Новый поиск", callback_data="search_new")
            builder.button(text="🔙 В меню", callback_data="consultant_menu")
            builder.adjust(2, 2)
            
            await message.answer(response, reply_markup=builder.as_markup(), parse_mode="Markdown")
            
        except Exception as e:
            log.error(f"Ошибка поиска: {e}", exc_info=True)
            await message.answer(f"❌ Ошибка поиска: {e}")


@router.callback_query(lambda c: c.data.startswith("search_page:"))
async def handle_search_pagination(callback: CallbackQuery):
    """Обработка пагинации результатов поиска"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        # Формат: search_page:запрос:страница
        _, query, page_str = callback.data.split(":", 2)
        page = int(page_str)
        
        await callback.answer()
        await perform_search(callback.message, query, page)
        
    except Exception as e:
        log.error(f"Ошибка пагинации: {e}", exc_info=True)
        await callback.answer("❌ Ошибка пагинации", show_alert=True)


@router.callback_query(lambda c: c.data == "search_quick")
async def handle_search_quick(callback: CallbackQuery, state: FSMContext):
    """Быстрый поиск"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.answer(
        "🔍 *Введите запрос для быстрого поиска:*\n\n"
        "Можно искать по:\n"
        "• ID пользователя (например, `576704037`)\n"
        "• Имени (например, `Максим`)\n"
        "• Username (например, `@username`)\n"
        "• Части текста",
        parse_mode="Markdown"
    )
    await state.set_state(SearchStates.waiting_search_query)


@router.message(SearchStates.waiting_search_query)
async def handle_search_query(message: Message, state: FSMContext):
    """Обработка запроса поиска"""
    query = message.text.strip()
    if not query:
        await message.answer("❌ Запрос не может быть пустым.")
        return
    
    await state.clear()
    await perform_search(message, query)


@router.callback_query(lambda c: c.data == "search_active")
async def handle_search_active(callback: CallbackQuery):
    """Поиск активных пользователей"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    async with session_maker() as session:
        service = UserSearchService(session)
        users, total = await service.search_users(is_active=True, active_days=7, limit=20)
        
        if not users:
            await callback.message.answer("❌ Нет активных пользователей за последние 7 дней.")
            return
        
        response = "📊 *Активные пользователи (последние 7 дней)*\n\n"
        for i, user in enumerate(users, 1):
            response += f"*{i}. ID:* `{user['user_id']}`\n"
            response += f"   *Последняя активность:* {user['last_active'][:10]}\n"
            response += f"   *Консультации:* {user['total_consultations']} | *Заказы:* {user['total_orders']}\n"
            response += "   " + "─" * 20 + "\n"
        
        await callback.message.answer(response, parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "search_paid")
async def handle_search_paid(callback: CallbackQuery):
    """Поиск платящих пользователей"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    async with session_maker() as session:
        service = UserSearchService(session)
        users, total = await service.search_users(has_paid_order=True, limit=20)
        
        if not users:
            await callback.message.answer("❌ Нет пользователей с оплаченными заказами.")
            return
        
        response = "💰 *Пользователи с оплаченными заказами*\n\n"
        for i, user in enumerate(users, 1):
            response += f"*{i}. ID:* `{user['user_id']}`\n"
            response += f"   *Оплаченных заказов:* {user['paid_orders']} из {user['total_orders']}\n"
            response += f"   *Консультаций:* {user['total_consultations']}\n"
            if user.get('last_order'):
                order = user['last_order']
                response += f"   *Последний заказ:* #{order['id']} ({order['created_at'][:10]})\n"
            response += "   " + "─" * 20 + "\n"
        
        await callback.message.answer(response, parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "search_stats")
async def handle_search_stats(callback: CallbackQuery):
    """Общая статистика"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    async with session_maker() as session:
        service = UserSearchService(session)
        stats = await service.get_global_stats()
        
        response = "📈 *Глобальная статистика*\n\n"
        response += f"*Всего пользователей:* {stats['total_users']}\n"
        response += f"*Активных (7 дней):* {stats['active_users']} ({stats['activity_rate']}%)\n"
        response += f"*С оплаченными заказами:* {stats['paid_users']} ({stats['conversion_rate']}%)\n"
        response += f"*Новых за сегодня:* {stats['new_users_today']}\n\n"
        
        response += "*Распределение по языкам:*\n"
        for lang, count in stats['languages'].items():
            response += f"  • {lang}: {count}\n"
        
        await callback.message.answer(response, parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "search_new")
async def handle_search_new(callback: CallbackQuery):
    """Новый поиск"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    await cmd_search(callback.message)


@router.message(Command("user"))
async def cmd_user_profile(message: Message, command: Optional[CommandObject] = None):
    """Детальный профиль пользователя"""
    if not is_consultant(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён.")
        return
    
    if not command or not command.args:
        await message.answer("❌ Укажите ID пользователя: `/user 576704037`")
        return
    
    try:
        user_id = int(command.args)
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом.")
        return
    
    async with session_maker() as session:
        try:
            profile = await get_user_full_profile(session, user_id)
            
            if "error" in profile:
                await message.answer(f"❌ Пользователь с ID `{user_id}` не найден.")
                return
            
            user = profile["user"]
            
            response = f"👤 *Детальный профиль пользователя*\n\n"
            response += f"*ID:* `{user['user_id']}`\n"
            response += f"*Язык:* {user['preferred_language']}\n"
            response += f"*Последняя активность:* {user['last_active'][:19] if user['last_active'] else 'нет данных'}\n"
            response += f"*Дата регистрации:* {user['created_at'][:19] if user['created_at'] else 'нет данных'}\n\n"
            
            response += f"*Статистика:*\n"
            response += f"• Консультаций: {user['total_consultations']}\n"
            response += f"• Заказов: {user['total_orders']} ({user['paid_orders']} оплачено)\n"
            response += f"• Предсказаний: {user['total_predictions']}\n"
            response += f"• Режим ИИ: {'✅' if user['ai_mode'] else '❌'}\n"
            response += f"• Гибридный режим: {'✅' if user['hybrid_mode'] else '❌'}\n"
            response += f"• AI запросы сегодня: {user['daily_ai_requests']}/{user['ai_requests_limit']}\n\n"
            
            if profile["orders"]:
                response += "*Последние заказы:*\n"
                for order in profile["orders"][:5]:
                    status_icon = "✅" if order["is_paid"] else "⏳"
                    response += f"• #{order['id']}: {order['question']} {status_icon}\n"
                response += "\n"
            
            if profile["predictions_by_type"]:
                response += "*Предсказания по типам:*\n"
                for pred_type, count in profile["predictions_by_type"].items():
                    response += f"• {pred_type}: {count}\n"
                response += f"*Всего:* {profile['total_predictions']}\n"
            
            await message.answer(response, parse_mode="Markdown")
            
        except Exception as e:
            log.error(f"Ошибка получения профиля: {e}", exc_info=True)
            await message.answer(f"❌ Ошибка получения профиля: {e}")