"""
Обработчики заказов консультаций.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.order import OrderService, OrderStatus
from bot.database.engine import create_engine, get_session_maker
from bot.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()
session_maker = None
if settings.is_database_configured:
    try:
        engine = create_engine(settings.DATABASE_URL)
        session_maker = get_session_maker(engine)
    except Exception as e:
        logger.error(f"Не удалось создать session_maker для заказов: {e}")


router = Router()


class OrderStates(StatesGroup):
    """Состояния оформления заказа"""
    waiting_order_data = State()      # Ожидание вопроса и даты рождения


def extract_birth_date(text: str) -> str:
    """Извлечь дату рождения из текста (формат ДД.ММ.ГГГГ)"""
    patterns = [
        r'(\d{1,2}\.\d{1,2}\.\d{4})',  # ДД.ММ.ГГГГ
        r'(\d{1,2}/\d{1,2}/\d{4})',    # ДД/ММ/ГГГГ
        r'(\d{1,2}-\d{1,2}-\d{4})',    # ДД-ММ-ГГГГ
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Приводим к формату ДД.ММ.ГГГГ
            date_str = match.group(1)
            date_str = date_str.replace('/', '.').replace('-', '.')
            # Проверяем валидность
            try:
                day, month, year = map(int, date_str.split('.'))
                datetime(year, month, day)
                return date_str
            except ValueError:
                continue
    return None


async def notify_admin(bot, order, admin_user_id: int = settings.ADMIN_USER_ID):
    """Уведомить администратора о новом заказе"""
    try:
        text = (
            f"🆕 *Новый заказ консультации #{order.id}*\n\n"
            f"👤 *Пользователь:* {order.first_name or 'не указано'}\n"
            f"📛 @{order.username or 'нет'}\n"
            f"🆔 ID: `{order.user_id}`\n"
            f"📅 *Дата рождения:* {order.birth_date}\n"
            f"❓ *Вопрос:*\n{order.question[:500]}"
        )
        await bot.send_message(
            admin_user_id,
            text,
            parse_mode="Markdown"
        )
        logger.info(f"Администратор уведомлён о заказе #{order.id}")
    except Exception as e:
        logger.error(f"Ошибка при уведомлении администратора: {e}")


@router.callback_query(F.data == "order_consultation")
async def start_order(callback: CallbackQuery, state: FSMContext, session_maker=None):
    """Начать оформление заказа"""
    await callback.answer()
    await state.set_state(OrderStates.waiting_order_data)
    await callback.message.answer(
        "📝 *Оформление заказа консультации*\n\n"
        "Пожалуйста, напишите ваш вопрос и дату рождения (в формате *ДД.ММ.ГГГГ*) одним сообщением.\n\n"
        "Пример: *«Меня беспокоит ситуация на работе, хочу понять перспективы. Дата рождения: 15.06.1990»*\n\n"
        "После получения ваших данных администратор свяжется с вами для подтверждения оплаты и отправки консультации.",
        parse_mode="Markdown"
    )


@router.message(OrderStates.waiting_order_data)
async def process_order_data(message: Message, state: FSMContext):
    """Обработка данных заказа"""
    user = message.from_user
    text = message.text.strip()

    # Извлекаем дату рождения
    birth_date = extract_birth_date(text)
    if not birth_date:
        await message.answer(
            "❌ *Не удалось найти дату рождения в формате ДД.ММ.ГГГГ*\n\n"
            "Пожалуйста, укажите дату рождения в правильном формате.\n"
            "Пример: *«Мой вопрос... Дата рождения: 15.06.1990»*",
            parse_mode="Markdown"
        )
        return

    # Вопрос — весь текст без даты рождения (убираем дату из текста)
    question = re.sub(r'\d{1,2}[\.\/\-]\d{1,2}[\.\/\-]\d{4}', '', text).strip()
    if len(question) < 5:
        await message.answer(
            "❌ *Вопрос слишком короткий*\n\n"
            "Пожалуйста, опишите вашу ситуацию подробнее.",
            parse_mode="Markdown"
        )
        return

    # Сохраняем заказ в БД
    if session_maker is None:
        logger.error("session_maker не инициализирован, заказ не будет сохранён")
        await message.answer(
            "❌ *Произошла ошибка при сохранении заказа (база данных не настроена)*\n\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    async with session_maker() as session:
        order_service = OrderService(session)
        try:
            order = await order_service.create_order(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                question=question,
                birth_date=birth_date,
            )
        except Exception as e:
            logger.error(f"Ошибка при создании заказа: {e}")
            await message.answer(
                "❌ *Произошла ошибка при сохранении заказа*\n\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode="Markdown"
            )
            await state.clear()
            return

    # Отправляем подтверждение пользователю
    await message.answer(
        "✅ *Ваш заказ принят!*\n\n"
        f"*Номер заказа:* #{order.id}\n"
        f"*Дата рождения:* {order.birth_date}\n"
        f"*Ваш вопрос:* {question[:200]}...\n\n"
        "Администратор проверит заявку и свяжется с вами в течение 24 часов.\n\n"
        "Спасибо за доверие! 🌟",
        parse_mode="Markdown"
    )

    # Уведомляем администратора
    await notify_admin(message.bot, order)

    await state.clear()


# Команда для просмотра заказов (только для администратора)
@router.message(F.text.contains("/orders"))
@router.message(F.text == "/orders")
async def cmd_orders(message: Message):
    """Показать новые заказы (администратор)"""
    # Проверяем, является ли пользователь администратором
    if message.from_user.id != settings.ADMIN_USER_ID:
        await message.answer("⛔️ Эта команда доступна только администратору.")
        return

    if session_maker is None:
        await message.answer("❌ База данных не настроена, заказы недоступны.")
        return
    
    async with session_maker() as session:
        order_service = OrderService(session)
        new_orders = await order_service.get_orders_by_status(OrderStatus.NEW, limit=10)
        completed_orders = await order_service.get_orders_by_status(OrderStatus.COMPLETED, limit=5)

        if not new_orders:
            text = "📭 *Новых заказов нет*"
        else:
            text = f"📋 *Новые заказы ({len(new_orders)}):*\n\n"
            for order in new_orders:
                text += (
                    f"🆔 *#{order.id}* | 👤 {order.first_name or 'не указано'} "
                    f"(ID: `{order.user_id}`)\n"
                    f"📅 {order.birth_date} | 🕒 {order.created_at.strftime('%d.%m %H:%M')}\n"
                    f"❓ {order.question[:100]}...\n\n"
                )

        if completed_orders:
            text += f"✅ *Выполненные заказы ({len(completed_orders)}):*\n"
            for order in completed_orders:
                text += f"#{order.id} — {order.first_name} ({order.updated_at.strftime('%d.%m')})\n"

        await message.answer(text, parse_mode="Markdown")
