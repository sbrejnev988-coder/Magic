"""
Обработчики истории консультаций с пагинацией и экспортом
"""

import logging
import tempfile
import os
from typing import List

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.history import ConsultationHistory

router = Router()
log = logging.getLogger(__name__)

CONSULTATIONS_PER_PAGE = 5


async def build_history_message(
    consultations: List,
    total_count: int,
    page: int,
    total_pages: int
) -> str:
    """Построить текст сообщения с историей консультаций."""
    if not consultations:
        return "📭 *История пуста*\nУ вас ещё нет сохранённых консультаций с AI."
    
    start_idx = (page - 1) * CONSULTATIONS_PER_PAGE + 1
    history_text = f"📚 *История консультаций (стр. {page}/{total_pages})*\n\n"
    
    for idx, consult in enumerate(consultations, start_idx):
        date_str = consult.created_at.strftime("%d.%m.%Y %H:%M")
        question_preview = consult.question[:50] + "..." if len(consult.question) > 50 else consult.question
        answer_preview = consult.answer[:80] + "..." if len(consult.answer) > 80 else consult.answer
        
        history_text += (
            f"*{idx}. {date_str}*\n"
            f"❓ *Вопрос:* {question_preview}\n"
            f"💭 *Ответ:* {answer_preview}\n"
            f"➖➖➖➖➖➖➖\n"
        )
    
    history_text += (
        f"\n📊 *Всего консультаций:* {total_count}\n"
        f"🗑️ _Вы можете удалить любую запись кнопкой ниже._"
    )
    
    return history_text


async def build_history_keyboard(
    consultations: List,
    page: int,
    total_pages: int,
    user_id: int
) -> InlineKeyboardMarkup:
    """Построить инлайн-клавиатуру для истории."""
    builder = InlineKeyboardBuilder()
    
    # Кнопки удаления для каждой консультации на странице
    for consult in consultations:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Удалить #{consult.id}",
                callback_data=f"delete_consult:{consult.id}:{page}"
            )
        )
    
    # Навигация
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"history_page:{page-1}")
        )
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"history_page:{page+1}")
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Дополнительные действия
    action_buttons = []
    if total_count > 0:
        action_buttons.append(
            InlineKeyboardButton(text="📥 Экспорт", callback_data=f"export_history:{user_id}")
        )
    action_buttons.append(
        InlineKeyboardButton(text="🔄 Обновить", callback_data=f"history_page:{page}")
    )
    
    builder.row(*action_buttons)
    
    return builder.as_markup()


@router.message(Command("history"))
async def cmd_history(message: Message, session_maker=None):
    """Показать историю консультаций пользователя (первая страница)."""
    await show_history_page(message, session_maker, page=1)


async def show_history_page(
    message_or_callback,
    session_maker,
    page: int = 1
):
    """Показать страницу истории консультаций."""
    if not session_maker:
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(
                "📂 *История консультаций временно недоступна*\n"
                "База данных не подключена. Попробуйте позже.",
                parse_mode="Markdown"
            )
        else:
            await message_or_callback.answer("Операция недоступна", show_alert=True)
        return
    
    user_id = message_or_callback.from_user.id
    
    try:
        async with session_maker() as session:
            # Получаем общее количество
            total_count = await ConsultationHistory.count_by_user(session, user_id)
            
            if total_count == 0:
                if isinstance(message_or_callback, Message):
                    await message_or_callback.answer(
                        "📭 *История пуста*\n"
                        "У вас ещё нет сохранённых консультаций с AI.\n"
                        "Используйте команду `/ask` для первой консультации.",
                        parse_mode="Markdown"
                    )
                else:
                    await message_or_callback.answer("История пуста", show_alert=True)
                return
            
            # Рассчитываем страницы
            total_pages = (total_count + CONSULTATIONS_PER_PAGE - 1) // CONSULTATIONS_PER_PAGE
            page = max(1, min(page, total_pages))
            offset = (page - 1) * CONSULTATIONS_PER_PAGE
            
            # Получаем консультации для страницы
            consultations = await ConsultationHistory.get_by_user(
                session, user_id, limit=CONSULTATIONS_PER_PAGE, offset=offset
            )
            
            # Строим сообщение и клавиатуру
            history_text = await build_history_message(
                consultations, total_count, page, total_pages
            )
            keyboard = await build_history_keyboard(
                consultations, page, total_pages, user_id
            )
            
            if isinstance(message_or_callback, Message):
                await message_or_callback.answer(
                    history_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            else:
                await message_or_callback.message.edit_text(
                    history_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                await message_or_callback.answer()
                
    except Exception as e:
        log.error(f"Ошибка при получении истории: {e}")
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(
                "⚠️ *Ошибка при загрузке истории*\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode="Markdown"
            )
        else:
            await message_or_callback.answer("Ошибка", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("history_page:"))
async def handle_history_page(callback: types.CallbackQuery, session_maker=None):
    """Обработка навигации по страницам истории."""
    try:
        page = int(callback.data.split(":")[1])
        await show_history_page(callback, session_maker, page)
    except Exception as e:
        log.error(f"Ошибка навигации: {e}")
        await callback.answer("Ошибка навигации", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("delete_consult:"))
async def delete_consultation(callback: types.CallbackQuery, session_maker=None):
    """Удалить консультацию."""
    if not session_maker:
        await callback.answer("Операция недоступна", show_alert=True)
        return
    
    try:
        data_parts = callback.data.split(":")
        consult_id = int(data_parts[1])
        page = int(data_parts[2]) if len(data_parts) > 2 else 1
        user_id = callback.from_user.id
        
        async with session_maker() as session:
            deleted = await ConsultationHistory.delete(session, consult_id, user_id)
            
            if deleted:
                # Показываем обновлённую страницу
                await show_history_page(callback, session_maker, page)
                await callback.answer(f"Консультация #{consult_id} удалена")
            else:
                await callback.answer("Консультация не найдена или недоступна", show_alert=True)
                
    except Exception as e:
        log.error(f"Ошибка при удалении консультации: {e}")
        await callback.answer("Ошибка при удалении", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("export_history:"))
async def export_history(callback: types.CallbackQuery, session_maker=None):
    """Экспортировать все консультации в текстовый файл."""
    if not session_maker:
        await callback.answer("Операция недоступна", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    try:
        async with session_maker() as session:
            # Получаем все консультации
            consultations = await ConsultationHistory.get_by_user(session, user_id, limit=1000)
            
            if not consultations:
                await callback.answer("Нет консультаций для экспорта", show_alert=True)
                return
            
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
                f.write(f"Экспорт консультаций MysticBot (пользователь {user_id})\n")
                f.write("=" * 50 + "\n\n")
                
                for consult in consultations:
                    date_str = consult.created_at.strftime("%d.%m.%Y %H:%M")
                    f.write(f"Консультация #{consult.id} от {date_str}\n")
                    f.write(f"Вопрос:\n{consult.question}\n\n")
                    f.write(f"Ответ:\n{consult.answer}\n")
                    f.write("-" * 40 + "\n\n")
                
                temp_path = f.name
            
            # Отправляем файл
            document = FSInputFile(temp_path, filename=f"consultations_{user_id}.txt")
            await callback.message.answer_document(
                document,
                caption=f"📥 *Экспорт консультаций*\nВсего: {len(consultations)} записей",
                parse_mode="Markdown"
            )
            
            # Удаляем временный файл
            os.unlink(temp_path)
            
            await callback.answer("Экспорт завершён")
            
    except Exception as e:
        log.error(f"Ошибка при экспорте истории: {e}")
        await callback.answer("Ошибка при экспорте", show_alert=True)


@router.message(Command("export"))
async def cmd_export(message: Message, session_maker=None):
    """Команда для экспорта истории консультаций."""
    # Просто отправляем callback для экспорта
    from aiogram.types import CallbackQuery
    fake_callback = CallbackQuery(
        id="0",
        from_user=message.from_user,
        chat_instance="0",
        message=message
    )
    fake_callback.data = f"export_history:{message.from_user.id}"
    await export_history(fake_callback, session_maker)