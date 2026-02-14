"""
Роутер для консультанта - просмотр истории, чеков, черновиков.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, desc

from bot.services.order import OrderService, OrderStatus
from bot.services.hybrid_draft import HybridDraftService
from bot.services.history import ConsultationHistory
from bot.services.user_settings import UserSettingsService
from bot.services.prediction_history_service import PredictionHistoryService
from bot.database.engine import create_engine, get_session_maker
from bot.models.consultation import Consultation
from bot.models.user_settings import UserSettings
from bot.config import Settings

log = logging.getLogger(__name__)

router = Router()
settings = Settings()

# Создаем engine и session_maker для работы с БД
engine = create_engine(settings.DATABASE_URL)
session_maker = get_session_maker(engine)

log.info(f"Consultant module loaded. ADMIN_USER_ID={settings.ADMIN_USER_ID}")


def is_consultant(user_id: int) -> bool:
    """Проверка прав консультанта"""
    # Приводим оба значения к int для надёжности
    user_id_int = int(user_id)
    admin_id_int = int(settings.ADMIN_USER_ID)
    
    result = user_id_int == admin_id_int
    log.info(f"CONSULTANT: Проверка прав: user_id={user_id_int}, ADMIN_USER_ID={admin_id_int}, результат={result}")
    return result


async def _check_consultant_access(callback: CallbackQuery) -> bool:
    """Проверка прав доступа для callback-обработчика"""
    user_id = callback.from_user.id
    if not is_consultant(user_id):
        log.warning(f"ACCESS DENIED for callback from user_id={user_id}")
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return False
    return True


def _create_pagination_keyboard(page: int, total_pages: int, prefix: str) -> InlineKeyboardBuilder:
    """Создаёт клавиатуру пагинации"""
    builder = InlineKeyboardBuilder()
    
    if page > 1:
        builder.button(text="◀️ Назад", callback_data=f"{prefix}:{page-1}")
    if page < total_pages:
        builder.button(text="Вперёд ▶️", callback_data=f"{prefix}:{page+1}")
    
    builder.button(text="🔙 В меню", callback_data="consultant_menu")
    builder.adjust(2)
    return builder


@router.message(Command("consultant"))
async def cmd_consultant(message: Message):
    """Главное меню консультанта"""
    if not is_consultant(message.from_user.id):
        await message.answer("⛔️ У вас нет прав консультанта.")
        return
    
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
    
    menu_text = """
👨‍💼 *Панель консультанта*

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
"""
    await message.answer(menu_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


async def _consultations_logic(user_id: int, chat_id: int, args: str = "", reply_to_message_id: int = None):
    """Логика просмотра консультаций (вынесена для reuse)"""
    if not is_consultant(user_id):
        log.warning(f"Access denied for user_id={user_id}")
        return False, "⛔️ Доступ запрещён."
    
    user_id_arg = None
    if args:
        try:
            user_id_arg = int(args)
        except ValueError:
            return False, "❌ Неверный формат ID пользователя. Использование: `/consultations [user_id]`"
    
    async with session_maker() as session:
        if user_id_arg:
            # Консультации конкретного пользователя
            consultations = await ConsultationHistory.get_by_user(session, user_id_arg, limit=20)
            if not consultations:
                return False, f"❌ У пользователя {user_id_arg} нет консультаций."
            
            response = f"📋 *Консультации пользователя {user_id_arg}* (последние 20)\n\n"
            for i, consult in enumerate(consultations, 1):
                response += f"*{i}.* {consult.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                response += f"   *Тема:* {consult.topic}\n"
                response += f"   *Сообщение:* {consult.message[:100]}...\n\n"
        else:
            # Последние 10 консультаций
            result = await session.execute(
                select(Consultation).order_by(Consultation.created_at.desc()).limit(10)
            )
            consultations = result.scalars().all()
            if not consultations:
                return False, "❌ В базе данных пока нет консультаций."
            
            response = "📋 *Последние 10 консультаций*\n\n"
            for i, consult in enumerate(consultations, 1):
                response += f"*{i}.* Пользователь ID: `{consult.user_id}`\n"
                response += f"   *Время:* {consult.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                response += f"   *Тема:* {consult.topic}\n"
                response += f"   *Сообщение:* {consult.message[:100]}...\n\n"
    
    return True, response


async def _orders_logic(user_id: int, chat_id: int, reply_to_message_id: int = None):
    """Логика просмотра заказов (вынесена для reuse)"""
    if not is_consultant(user_id):
        log.warning(f"Access denied for user_id={user_id}")
        return False, "⛔️ Доступ запрещён.", None
    
    async with session_maker() as session:
        # Получаем заказы, отсортированные по дате
        orders = await OrderService(session).get_all_orders(limit=20)
        
        if not orders:
            return True, "📭 *Нет заказов.*", None
        
        # Разделяем оплаченные и неоплаченные
        paid_orders = [o for o in orders if o.is_paid]
        unpaid_orders = [o for o in orders if not o.is_paid]
        
        response = "💰 *Заказы для проверки:*\n\n"
        response += f"✅ *Оплачено:* {len(paid_orders)} заказов\n"
        response += f"⏳ *Ожидают оплаты:* {len(unpaid_orders)} заказов\n\n"
        
        # Показываем последние 5 ожидающих оплаты
        if unpaid_orders:
            response += "*Последние ожидающие оплаты:*\n"
            for order in unpaid_orders[:5]:
                user_info = f"👤 {order.user_id}"
                user_settings = await UserSettingsService.get_by_user_id(session, order.user_id)
                if user_settings and user_settings.first_name:
                    user_info = f"👤 {user_settings.first_name}"
                
                response += f"🆔 *Заказ #{order.id}*\n"
                response += f"   {user_info} (ID: {order.user_id})\n"
                response += f"   💰 Сумма: {order.amount or 777} ₽\n"
                response += f"   📅 Создан: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                if order.payment_screenshot:
                    response += f"   📸 *Есть скриншот*\n"
                response += "—" * 30 + "\n"
        
        # Создаем inline-клавиатуру
        builder = InlineKeyboardBuilder()
        if unpaid_orders:
            builder.row(
                types.InlineKeyboardButton(text="👁️ Проверить скриншоты", callback_data="consultant_check_screenshots"),
                types.InlineKeyboardButton(text="✅ Отметить оплаченными", callback_data="consultant_mark_paid")
            )
        builder.row(
            types.InlineKeyboardButton(text="📋 Все заказы", callback_data="consultant_all_orders"),
            types.InlineKeyboardButton(text="🔙 В меню", callback_data="consultant_menu")
        )
        
        return True, response, builder.as_markup()


async def _drafts_logic(user_id: int, chat_id: int, reply_to_message_id: int = None):
    """Логика просмотра черновиков (вынесена для reuse)"""
    if not is_consultant(user_id):
        log.warning(f"Access denied for user_id={user_id}")
        return False, "⛔️ Доступ запрещён.", None
    
    async with session_maker() as session:
        # Получаем черновики, ожидающие проверки
        pending_drafts = await HybridDraftService.get_pending_drafts(session, limit=20)
        
        if not pending_drafts:
            return True, "✅ *Нет черновиков, ожидающих проверки.*", None
        
        # Показываем список черновиков
        response = "📝 *Черновики на проверку:*\n\n"
        for draft in pending_drafts:
            response += f"🆔 *Черновик #{draft.id}*\n"
            response += f"👤 Пользователь: {draft.first_name or 'Неизвестно'} (@{draft.username or 'нет'})\n"
            response += f"❓ Вопрос: {draft.question[:100]}...\n"
            response += f"🕒 Создан: {draft.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            response += "—" * 30 + "\n"
        
        return True, response, None  # Для черновиков кнопки создаются отдельно для каждого


async def _stats_logic(user_id: int, chat_id: int, reply_to_message_id: int = None):
    """Логика просмотра статистики (вынесена для reuse)"""
    if not is_consultant(user_id):
        log.warning(f"Access denied for user_id={user_id}")
        return False, "⛔️ Доступ запрещён.", None
    
    async with session_maker() as session:
        # Получаем базовую статистику
        # 1. Общее количество пользователей
        from bot.models.user_settings import UserSettings
        stmt = select(UserSettings)
        result = await session.execute(stmt)
        all_users = result.scalars().all()
        total_users = len(all_users)
        
        # 2. Активные пользователи (за последние 7 дней)
        week_ago = datetime.utcnow() - timedelta(days=7)
        # Нужно добавить поле last_activity в UserSettings, пока заглушка
        active_users = total_users  # заглушка
        
        # 3. Консультации за сегодня
        today = datetime.utcnow().date()
        stmt = select(Consultation).where(Consultation.created_at >= datetime(today.year, today.month, today.day))
        result = await session.execute(stmt)
        today_consultations = len(result.scalars().all())
        
        # 4. Заказы
        orders = await OrderService(session).get_all_orders()
        total_orders = len(orders)
        paid_orders = len([o for o in orders if o.is_paid])
        
        # 5. Черновики
        all_drafts = await HybridDraftService.get_all_drafts(session)
        pending_drafts = len([d for d in all_drafts if d.status == "pending"])
        
        stats_text = f"""
📊 *Статистика для консультанта*

👥 *Пользователи:*
• Всего: {total_users}
• Активные (7 дней): {active_users}

💬 *Консультации:*
• Сегодня: {today_consultations}
• Всего: {len(all_drafts) + today_consultations} (примерно)

💰 *Заказы:*
• Всего: {total_orders}
• Оплачено: {paid_orders}
• Ожидают: {total_orders - paid_orders}

📝 *Черновики:*
• Ожидают проверки: {pending_drafts}
• Всего черновиков: {len(all_drafts)}

⏰ *Обновлено:* {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        # Создаем inline-клавиатуру
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="🔄 Обновить", callback_data="consultant_stats_refresh"),
            types.InlineKeyboardButton(text="📈 Детальная статистика", callback_data="consultant_detailed_stats")
        )
        
        return True, stats_text, builder.as_markup()


@router.message(Command("consultations"))
async def cmd_consultations(message: Message, command: CommandObject):
    """Просмотр консультаций (последние 10 или по пользователю)"""
    log.debug(f"cmd_consultations called by user_id={message.from_user.id}, args={command.args}")
    log.debug(f"Settings ADMIN_USER_ID={settings.ADMIN_USER_ID}")
    
    success, result = await _consultations_logic(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        args=command.args,
        reply_to_message_id=message.message_id
    )
    if not success:
        await message.answer(result, parse_mode="Markdown")
    else:
        await message.answer(result, parse_mode="Markdown")


@router.message(Command("orders"))
async def cmd_orders_consultant(message: Message):
    """Просмотр заказов (особенно с оплатой)"""
    success, result, markup = await _orders_logic(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        reply_to_message_id=message.message_id
    )
    
    if not success:
        await message.answer(result, parse_mode="Markdown")
        return
    
    # Отправляем основное сообщение
    await message.answer(result, parse_mode="Markdown")
    
    # Отправляем сообщение с кнопками, если есть
    if markup:
        await message.answer("Действия:", reply_markup=markup)


@router.message(Command("drafts"))
async def cmd_drafts_consultant(message: Message):
    """Просмотр черновиков на проверку (аналог /admin_drafts)"""
    success, result, _ = await _drafts_logic(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        reply_to_message_id=message.message_id
    )
    
    if not success:
        await message.answer(result, parse_mode="Markdown")
        return
    
    # Отправляем список черновиков
    await message.answer(result, parse_mode="Markdown")
    
    # Для каждого черновика создаем inline-кнопки
    async with session_maker() as session:
        pending_drafts = await HybridDraftService.get_pending_drafts(session, limit=20)
        
        for draft in pending_drafts:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="👀 Просмотреть", callback_data=f"consultant_view_draft:{draft.id}"),
                types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"consultant_approve_draft:{draft.id}")
            )
            builder.row(
                types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"consultant_edit_draft:{draft.id}"),
                types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"consultant_reject_draft:{draft.id}")
            )
            
            draft_text = (
                f"🆔 *Черновик #{draft.id}*\n"
                f"👤 Пользователь: {draft.first_name or 'Неизвестно'} (@{draft.username or 'нет'})\n"
                f"❓ Вопрос: {draft.question[:200]}..."
            )
            await message.answer(draft_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats_consultant(message: Message):
    """Статистика для консультанта"""
    success, result, markup = await _stats_logic(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        reply_to_message_id=message.message_id
    )
    
    if not success:
        await message.answer(result, parse_mode="Markdown")
        return
    
    # Отправляем статистику
    await message.answer(result, parse_mode="Markdown")
    
    # Отправляем сообщение с кнопками, если есть
    if markup:
        await message.answer("Действия:", reply_markup=markup)


# Callback handlers для меню
@router.callback_query(lambda c: c.data == "consultant_menu")
async def handle_consultant_menu(callback: CallbackQuery):
    """Возврат в меню консультанта"""
    if not await _check_consultant_access(callback):
        return
    
    await callback.answer()
    
    # Создаем меню с inline-кнопками (дублируем логику из cmd_consultant)
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
    
    menu_text = """
👨‍💼 *Панель консультанта*

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
"""
    await callback.message.answer(menu_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "consultant_consultations")
async def handle_consultant_consultations(callback: CallbackQuery):
    """Просмотр консультаций через callback"""
    if not await _check_consultant_access(callback):
        return
    
    await callback.answer()
    success, result = await _consultations_logic(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        args="",
        reply_to_message_id=callback.message.message_id
    )
    if not success:
        await callback.message.answer(result, parse_mode="Markdown")
    else:
        await callback.message.answer(result, parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "consultant_orders")
async def handle_consultant_orders(callback: CallbackQuery):
    """Просмотр заказов через callback"""
    if not await _check_consultant_access(callback):
        return
    
    await callback.answer()
    success, result, markup = await _orders_logic(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        reply_to_message_id=callback.message.message_id
    )
    
    if not success:
        await callback.message.answer(result, parse_mode="Markdown")
        return
    
    # Отправляем основное сообщение
    await callback.message.answer(result, parse_mode="Markdown")
    
    # Отправляем сообщение с кнопками, если есть
    if markup:
        await callback.message.answer("Действия:", reply_markup=markup)


@router.callback_query(lambda c: c.data == "consultant_drafts")
async def handle_consultant_drafts(callback: CallbackQuery):
    """Просмотр черновиков через callback"""
    if not await _check_consultant_access(callback):
        return
    
    await callback.answer()
    success, result, _ = await _drafts_logic(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        reply_to_message_id=callback.message.message_id
    )
    
    if not success:
        await callback.message.answer(result, parse_mode="Markdown")
        return
    
    # Отправляем список черновиков
    await callback.message.answer(result, parse_mode="Markdown")
    
    # Для каждого черновика создаем inline-кнопки
    async with session_maker() as session:
        pending_drafts = await HybridDraftService.get_pending_drafts(session, limit=20)
        
        for draft in pending_drafts:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="👀 Просмотреть", callback_data=f"consultant_view_draft:{draft.id}"),
                types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"consultant_approve_draft:{draft.id}")
            )
            builder.row(
                types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"consultant_edit_draft:{draft.id}"),
                types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"consultant_reject_draft:{draft.id}")
            )
            
            draft_text = (
                f"🆔 *Черновик #{draft.id}*\n"
                f"👤 Пользователь: {draft.first_name or 'Неизвестно'} (@{draft.username or 'нет'})\n"
                f"❓ Вопрос: {draft.question[:200]}..."
            )
            await callback.message.answer(draft_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "consultant_stats")
async def handle_consultant_stats(callback: CallbackQuery):
    """Просмотр статистики через callback"""
    if not await _check_consultant_access(callback):
        return
    
    await callback.answer()
    success, result, markup = await _stats_logic(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        reply_to_message_id=callback.message.message_id
    )
    
    if not success:
        await callback.message.answer(result, parse_mode="Markdown")
        return
    
    # Отправляем статистику
    await callback.message.answer(result, parse_mode="Markdown")
    
    # Отправляем сообщение с кнопками, если есть
    if markup:
        await callback.message.answer("Действия:", reply_markup=markup)


@router.callback_query(lambda c: c.data == "consultant_search_user")
async def handle_consultant_search_user(callback: CallbackQuery):
    """Поиск пользователя через callback"""
    if not await _check_consultant_access(callback):
        return
    
    await callback.answer()
    
    # Отправляем инструкцию по использованию команды /search
    help_text = """
🔍 *Поиск пользователя*

Используйте команду `/search` с параметрами для расширенного поиска.

*Примеры:*
`/search` — показать всех пользователей (постранично)
`/search активные` — пользователи с активностью за последние 7 дней
`/search оплатившие` — пользователи с оплаченными заказами
`/search язык:ru` — пользователи с русским языком
`/search консультации:5` — пользователи с 5+ консультациями

*Также можно искать по ID пользователя:*
`/user 123456789` — подробная информация о пользователе

Для быстрого поиска введите команду `/search` и следуйте подсказкам.
"""
    await callback.message.answer(help_text, parse_mode="Markdown")


# Callback handlers для черновиков
@router.callback_query(lambda c: c.data.startswith("consultant_view_draft:"))
async def handle_consultant_view_draft(callback: CallbackQuery):
    """Просмотр деталей черновика"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with session_maker() as session:
        draft = await HybridDraftService.get_draft_by_id(session, draft_id)
        
        if not draft:
            await callback.answer("❌ Черновик не найден.", show_alert=True)
            return
        
        details = (
            f"📋 *Детали черновика #{draft.id}*\n\n"
            f"👤 *Пользователь:*\n"
            f"• ID: {draft.user_id}\n"
            f"• Имя: {draft.first_name or 'Неизвестно'}\n"
            f"• Username: @{draft.username or 'нет'}\n\n"
            f"❓ *Вопрос:*\n{draft.question}\n\n"
            f"🤖 *Черновик ИИ:*\n{draft.ai_draft[:2000]}"
        )
        if len(draft.ai_draft) > 2000:
            details += "\n... (текст обрезан)"
        
        details += f"\n\n📊 *Статус:* {draft.status.value}"
        if draft.reviewer_id:
            details += f"\n👨‍💼 *Проверяющий:* {draft.reviewer_id}"
        if draft.reviewer_notes:
            details += f"\n📝 *Заметки проверяющего:*\n{draft.reviewer_notes}"
        
        details += f"\n\n🕒 *Создан:* {draft.created_at.strftime('%d.%m.%Y %H:%M')}"
        if draft.reviewed_at:
            details += f"\n✏️ *Проверен:* {draft.reviewed_at.strftime('%d.%m.%Y %H:%M')}"
        
        await callback.answer()
        await callback.message.answer(details, parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("consultant_approve_draft:"))
async def handle_consultant_approve_draft(callback: CallbackQuery):
    """Одобрение черновика (отправка как есть)"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with session_maker() as session:
        draft = await HybridDraftService.approve_draft(
            session=session,
            draft_id=draft_id,
            reviewer_id=callback.from_user.id,
            final_answer=None,  # отправляем как есть
            reviewer_notes="Одобрено консультантом без изменений."
        )
        
        if not draft:
            await callback.answer("❌ Черновик не найден.", show_alert=True)
            return
        
        # Отправляем ответ пользователю
        try:
            await callback.bot.send_message(
                chat_id=draft.user_id,
                text=f"✅ *Ваш черновик проверен консультантом*\n\n{draft.final_answer or draft.ai_draft}",
                parse_mode="Markdown"
            )
            # Помечаем как отправленный
            await HybridDraftService.mark_as_sent(session, draft_id)
            await callback.answer("✅ Черновик одобрен и отправлен пользователю.")
            
            # Обновляем сообщение
            await callback.message.edit_text(
                f"✅ *Черновик #{draft_id} одобрен и отправлен пользователю.*",
                parse_mode="Markdown"
            )
        except Exception as e:
            log.error(f"Ошибка при отправке черновика пользователю: {e}")
            await callback.answer("✅ Черновик одобрен, но не удалось отправить пользователю.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("consultant_reject_draft:"))
async def handle_consultant_reject_draft(callback: CallbackQuery, state: FSMContext):
    """Отклонение черновика"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    # Сохраняем draft_id в состоянии и просим причину отклонения
    await state.update_data(consultant_reject_draft_id=draft_id)
    await callback.answer()
    
    await callback.message.answer(
        f"❌ *Отклонение черновика #{draft_id}*\n\n"
        "Укажите причину отклонения (это будет сохранено в заметках):",
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data.startswith("consultant_edit_draft:"))
async def handle_consultant_edit_draft(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования черновика консультантом"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    # Сохраняем draft_id в состоянии
    await state.update_data(consultant_edit_draft_id=draft_id)
    await callback.answer()
    
    await callback.message.answer(
        f"✏️ *Редактирование черновика #{draft_id}*\n\n"
        "Отправьте исправленный текст ответа. Вы можете полностью изменить текст или отредактировать частично.\n\n"
        "Когда закончите — просто отправьте сообщение.",
        parse_mode="Markdown"
    )


# Callback handlers для заказов
@router.callback_query(lambda c: c.data == "consultant_check_screenshots")
async def handle_consultant_check_screenshots(callback: CallbackQuery):
    """Показать заказы со скриншотами для проверки"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    
    async with session_maker() as session:
        # Заказы с скриншотами, но не оплаченные
        orders = await OrderService(session).get_all_orders()
        orders_with_screenshots = [o for o in orders if o.payment_screenshot and not o.is_paid]
        
        if not orders_with_screenshots:
            await callback.message.answer("✅ *Нет заказов со скриншотами для проверки.*", parse_mode="Markdown")
            return
        
        response = "📸 *Заказы со скриншотами для проверки:*\n\n"
        for order in orders_with_screenshots[:10]:  # первые 10
            user_info = f"👤 {order.user_id}"
            user_settings = await UserSettingsService.get_by_user_id(session, order.user_id)
            if user_settings and user_settings.first_name:
                user_info = f"👤 {user_settings.first_name}"
            
            response += f"🆔 *Заказ #{order.id}*\n"
            response += f"   {user_info} (ID: {order.user_id})\n"
            response += f"   💰 Сумма: {order.amount or 777} ₽\n"
            response += f"   📅 Создан: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            response += f"   [Проверить скриншот](#order_{order.id})\n"
            response += "—" * 30 + "\n"
        
        await callback.message.answer(response, parse_mode="Markdown")
        
        # Кнопки для каждого заказа
        for order in orders_with_screenshots[:5]:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="👁️ Просмотреть скриншот", callback_data=f"consultant_view_screenshot:{order.id}"),
                types.InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"consultant_confirm_payment:{order.id}")
            )
            builder.row(
                types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"consultant_reject_payment:{order.id}")
            )
            await callback.message.answer(
                f"🆔 *Заказ #{order.id}*\nПользователь ID: {order.user_id}",
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )


@router.callback_query(lambda c: c.data == "consultant_all_orders")
async def handle_consultant_all_orders(callback: CallbackQuery):
    """Показать все заказы"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    success, result, markup = await _orders_logic(
        user_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        reply_to_message_id=callback.message.message_id
    )
    
    if not success:
        await callback.message.answer(result, parse_mode="Markdown")
        return
    
    # Отправляем основное сообщение
    await callback.message.answer(result, parse_mode="Markdown")
    
    # Отправляем сообщение с кнопками, если есть
    if markup:
        await callback.message.answer("Действия:", reply_markup=markup)


@router.callback_query(lambda c: c.data.startswith("consultant_view_screenshot:"))
async def handle_consultant_view_screenshot(callback: CallbackQuery):
    """Просмотр скриншота оплаты"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with session_maker() as session:
        order = await OrderService(session).get_order_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден.", show_alert=True)
            return
        
        if not order.payment_screenshot:
            await callback.answer("❌ У этого заказа нет скриншота.", show_alert=True)
            return
        
        # Отправляем информацию о заказе
        user_info = f"👤 {order.user_id}"
        user_settings = await UserSettingsService.get_by_user_id(session, order.user_id)
        if user_settings and user_settings.first_name:
            user_info = f"👤 {user_settings.first_name} (ID: {order.user_id})"
        
        response = (
            f"📸 *Скриншот оплаты для заказа #{order.id}*\n\n"
            f"{user_info}\n"
            f"💰 Сумма: {order.amount or 777} ₽\n"
            f"📅 Дата заказа: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"✅ Оплачен: {'Да' if order.is_paid else 'Нет'}\n\n"
            f"File ID: `{order.payment_screenshot}`\n\n"
            f"*Действия:*"
        )
        
        builder = InlineKeyboardBuilder()
        if not order.is_paid:
            builder.row(
                types.InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"consultant_confirm_payment:{order.id}"),
                types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"consultant_reject_payment:{order.id}")
            )
        builder.row(
            types.InlineKeyboardButton(text="🔙 Назад к заказам", callback_data="consultant_orders")
        )
        
        await callback.answer()
        await callback.message.answer(response, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("consultant_confirm_payment:"))
async def handle_consultant_confirm_payment(callback: CallbackQuery):
    """Подтверждение оплаты заказа"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with session_maker() as session:
        success = await OrderService(session).mark_as_paid(order_id)
        
        if not success:
            await callback.answer("❌ Заказ не найден или уже оплачен.", show_alert=True)
            return
        
        # Уведомляем пользователя
        order = await OrderService(session).get_order_by_id(order_id)
        if order:
            try:
                await callback.bot.send_message(
                    chat_id=order.user_id,
                    text=f"✅ *Ваш заказ #{order_id} подтверждён!*\n\n"
                         f"Оплата подтверждена консультантом. Теперь у вас есть доступ к ИИ-режиму.\n"
                         f"Спасибо за покупку!",
                    parse_mode="Markdown"
                )
            except Exception as e:
                log.error(f"Ошибка при уведомлении пользователя: {e}")
        
        await callback.answer("✅ Оплата подтверждена. Пользователь уведомлён.")
        await callback.message.edit_text(
            f"✅ *Заказ #{order_id} подтверждён как оплаченный.*",
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data.startswith("consultant_reject_payment:"))
async def handle_consultant_reject_payment(callback: CallbackQuery, state: FSMContext):
    """Отклонение оплаты (требуется причина)"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    # Сохраняем order_id в состоянии и просим причину
    await state.update_data(consultant_reject_payment_order_id=order_id)
    await callback.answer()
    
    await callback.message.answer(
        f"❌ *Отклонение оплаты заказа #{order_id}*\n\n"
        "Укажите причину отклонения (почему скриншот не подходит):",
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data == "consultant_mark_paid")
async def handle_consultant_mark_paid(callback: CallbackQuery):
    """Массовое подтверждение оплаты (показывает список)"""
    if not is_consultant(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    await callback.answer()
    
    async with session_maker() as session:
        # Заказы с скриншотами, но не оплаченные
        orders = await OrderService(session).get_all_orders()
        unpaid_with_screenshots = [o for o in orders if o.payment_screenshot and not o.is_paid]
        
        if not unpaid_with_screenshots:
            await callback.message.answer("✅ *Нет заказов со скриншотами для массового подтверждения.*", parse_mode="Markdown")
            return
        
        response = "💰 *Массовое подтверждение оплаты:*\n\n"
        response += f"Найдено {len(unpaid_with_screenshots)} заказов со скриншотами, ожидающих оплаты.\n\n"
        response += "*Список:*\n"
        for order in unpaid_with_screenshots[:10]:
            user_info = f"👤 {order.user_id}"
            user_settings = await UserSettingsService.get_by_user_id(session, order.user_id)
            if user_settings and user_settings.first_name:
                user_info = f"👤 {user_settings.first_name}"
            
            response += f"🆔 *Заказ #{order.id}* — {user_info}\n"
        
        response += "\n*Используйте кнопки ниже для подтверждения каждого заказа.*"
        
        await callback.message.answer(response, parse_mode="Markdown")
        
        # Показываем кнопки для каждого заказа
        for order in unpaid_with_screenshots[:5]:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text=f"✅ Подтвердить заказ #{order.id}", callback_data=f"consultant_confirm_payment:{order.id}")
            )
            await callback.message.answer(
                f"🆔 *Заказ #{order.id}*\nПользователь ID: {order.user_id}",
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )


# Обработчики сообщений для состояний FSM
@router.message(F.text & F.from_user.id == settings.ADMIN_USER_ID)
async def handle_consultant_text(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений от консультанта (для редактирования/отклонения черновиков)"""
    data = await state.get_data()
    
    # Проверяем, редактируем ли черновик
    draft_id = data.get("consultant_edit_draft_id")
    if draft_id:
        edited_text = message.text.strip()
        if not edited_text:
            await message.answer("❌ Текст не может быть пустым.")
            return
        
        async with session_maker() as session:
            draft = await HybridDraftService.approve_draft(
                session=session,
                draft_id=draft_id,
                reviewer_id=message.from_user.id,
                final_answer=edited_text,
                reviewer_notes="Отредактировано консультантом."
            )
            
            if not draft:
                await message.answer("❌ Черновик не найден.")
                await state.clear()
                return
            
            # Отправляем ответ пользователю
            try:
                await message.bot.send_message(
                    chat_id=draft.user_id,
                    text=f"✅ *Ваш черновик проверен и отредактирован консультантом*\n\n{draft.final_answer}",
                    parse_mode="Markdown"
                )
                # Помечаем как отправленный
                await HybridDraftService.mark_as_sent(session, draft_id)
                await message.answer(f"✅ Черновик #{draft_id} отредактирован и отправлен пользователю.")
            except Exception as e:
                log.error(f"Ошибка при отправке черновика пользователю: {e}")
                await message.answer("✅ Черновик отредактирован, но не удалось отправить пользователю.")
        
        await state.clear()
        return
    
    # Проверяем, отклоняем ли черновик
    reject_draft_id = data.get("consultant_reject_draft_id")
    if reject_draft_id:
        reason = message.text.strip()
        if not reason:
            await message.answer("❌ Причина не может быть пустой.")
            return
        
        async with session_maker() as session:
            draft = await HybridDraftService.reject_draft(
                session=session,
                draft_id=reject_draft_id,
                reviewer_id=message.from_user.id,
                reviewer_notes=reason
            )
            
            if not draft:
                await message.answer("❌ Черновик не найден.")
                await state.clear()
                return
            
            # Уведомляем пользователя об отклонении
            try:
                await message.bot.send_message(
                    chat_id=draft.user_id,
                    text=f"❌ *Ваш черновик отклонён консультантом*\n\n"
                         f"Причина: {reason}\n\n"
                         f"Вы можете задать новый вопрос или отредактировать существующий.",
                    parse_mode="Markdown"
                )
                await message.answer(f"✅ Черновик #{reject_draft_id} отклонён. Пользователь уведомлён.")
            except Exception as e:
                log.error(f"Ошибка при уведомлении пользователя: {e}")
                await message.answer(f"✅ Черновик #{reject_draft_id} отклонён, но не удалось уведомить пользователя.")
        
        await state.clear()
        return
    
    # Проверяем, отклоняем ли оплату
    reject_payment_order_id = data.get("consultant_reject_payment_order_id")
    if reject_payment_order_id:
        reason = message.text.strip()
        if not reason:
            await message.answer("❌ Причина не может быть пустой.")
            return
        
        async with session_maker() as session:
            order = await OrderService(session).get_order_by_id(reject_payment_order_id)
            if not order:
                await message.answer("❌ Заказ не найден.")
                await state.clear()
                return
            
            # Можно обновить статус заказа или добавить заметку
            # Пока просто уведомляем пользователя
            try:
                await message.bot.send_message(
                    chat_id=order.user_id,
                    text=f"❌ *Оплата по заказу #{reject_payment_order_id} отклонена*\n\n"
                         f"Причина: {reason}\n\n"
                         f"Пожалуйста, предоставьте корректный скриншот оплаты или обратитесь в поддержку.",
                    parse_mode="Markdown"
                )
                await message.answer(f"✅ Оплата заказа #{reject_payment_order_id} отклонена. Пользователь уведомлён.")
            except Exception as e:
                log.error(f"Ошибка при уведомлении пользователя: {e}")
                await message.answer(f"✅ Оплата отклонена, но не удалось уведомить пользователя.")
        
        await state.clear()
        return
    
    # Если не редактирование и не отклонение, возможно, это обычное сообщение
    # Игнорируем