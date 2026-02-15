"""
Обработчики для работы с историей предсказаний пользователя.
"""

import logging
from datetime import datetime, timedelta

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from bot.services.prediction_history_service import PredictionHistoryService
from bot.models.prediction_history import PredictionType
from bot.database.engine import get_session_maker

router = Router()
log = logging.getLogger(__name__)


@router.message(Command("my_predictions"))
async def cmd_my_predictions(message: Message):
    """Показать историю предсказаний пользователя"""
    user_id = message.from_user.id
    
    async with get_session_maker()() as session:
        # Получаем статистику
        stats = await PredictionHistoryService.get_user_statistics(session, user_id)
        
        if stats["total"] == 0:
            await message.answer(
                "📭 *У вас пока нет истории предсказаний.*\n\n"
                "Используйте функции бота (Таро, Руны, Гороскоп и др.), "
                "чтобы создать первую запись в истории.",
                parse_mode="Markdown"
            )
            return
        
        # Формируем текст со статистикой
        stats_text = f"""
📊 *Ваша история предсказаний*

*Всего предсказаний:* {stats['total']}
*Сегодня:* {stats['today_count']}

*По типам:*
"""
        for pred_type, count in stats["by_type"].items():
            type_name = pred_type.replace("_", " ").title()
            stats_text += f"• {type_name}: {count}\n"
        
        if stats["last_prediction"]:
            last = stats["last_prediction"]
            last_type = last["prediction_type"].replace("_", " ").title()
            last_time = datetime.fromisoformat(last["created_at"]).strftime("%d.%m.%Y %H:%M")
            stats_text += f"\n*Последнее предсказание:*\n"
            stats_text += f"Тип: {last_type}\n"
            stats_text += f"Дата: {last_time}\n"
            stats_text += f"Текст: {last['result_text'][:100]}..."
        
        await message.answer(stats_text, parse_mode="Markdown")
        
        # Кнопки для детального просмотра
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="📋 Последние 10", callback_data="predictions_recent:10"),
            types.InlineKeyboardButton(text="📈 Статистика", callback_data="predictions_stats")
        )
        builder.row(
            types.InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="predictions_clear_confirm")
        )
        
        await message.answer("Действия:", reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data.startswith("predictions_recent:"))
async def handle_predictions_recent(callback: CallbackQuery):
    """Показать последние предсказания"""
    try:
        limit = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        limit = 10
    
    user_id = callback.from_user.id
    
    async with get_session_maker()() as session:
        predictions = await PredictionHistoryService.get_by_user(session, user_id, limit=limit)
        
        if not predictions:
            await callback.answer("📭 Нет предсказаний.", show_alert=True)
            return
        
        response = f"📋 *Ваши последние {len(predictions)} предсказаний:*\n\n"
        
        for i, pred in enumerate(predictions, 1):
            pred_type = pred.prediction_type.value.replace("_", " ").title()
            time_str = pred.created_at.strftime("%d.%m.%Y %H:%M")
            response += f"*{i}. {pred_type}* ({time_str})\n"
            if pred.subtype:
                subtype_display = pred.subtype.replace("_", " ").title()
                response += f"   *Вид:* {subtype_display}\n"
            response += f"   {pred.result_text[:80]}...\n"
            response += f"   [Подробнее](#pred_{pred.id})\n"
            response += "—" * 30 + "\n"
        
        await callback.message.answer(response, parse_mode="Markdown")
        await callback.answer()


@router.callback_query(lambda c: c.data == "predictions_stats")
async def handle_predictions_stats(callback: CallbackQuery):
    """Подробная статистика предсказаний"""
    user_id = callback.from_user.id
    
    async with get_session_maker()() as session:
        stats = await PredictionHistoryService.get_user_statistics(session, user_id)
        
        if stats["total"] == 0:
            await callback.answer("📭 Нет данных для статистики.", show_alert=True)
            return
        
        # Детальная статистика по типам
        stats_text = f"""
📈 *Детальная статистика предсказаний*

*Общее количество:* {stats['total']}
*За сегодня:* {stats['today_count']}

*Распределение по типам:*
"""
        for pred_type, count in stats["by_type"].items():
            percentage = (count / stats["total"]) * 100
            type_name = pred_type.replace("_", " ").title()
            stats_text += f"• *{type_name}*: {count} ({percentage:.1f}%)\n"
        
        # Самый популярный тип
        if stats["by_type"]:
            popular_type = max(stats["by_type"].items(), key=lambda x: x[1])
            popular_name = popular_type[0].replace("_", " ").title()
            stats_text += f"\n*Самый популярный тип:* {popular_name} ({popular_type[1]} раз)"
        
        await callback.message.answer(stats_text, parse_mode="Markdown")
        await callback.answer()


@router.callback_query(lambda c: c.data == "predictions_clear_confirm")
async def handle_predictions_clear_confirm(callback: CallbackQuery):
    """Подтверждение очистки истории"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="✅ Да, очистить", callback_data="predictions_clear_yes"),
        types.InlineKeyboardButton(text="❌ Нет, отмена", callback_data="predictions_clear_no")
    )
    
    await callback.message.answer(
        "⚠️ *Очистка истории предсказаний*\n\n"
        "Вы уверены, что хотите удалить всю историю ваших предсказаний?\n"
        "Это действие нельзя отменить.\n\n"
        "Все записи о предсказаниях (Таро, Руны, Гороскопы и др.) будут удалены.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "predictions_clear_yes")
async def handle_predictions_clear_yes(callback: CallbackQuery):
    """Очистка истории предсказаний"""
    user_id = callback.from_user.id
    
    async with get_session_maker()() as session:
        # Получаем все ID предсказаний пользователя
        predictions = await PredictionHistoryService.get_by_user(session, user_id, limit=1000)
        deleted_count = 0
        
        for pred in predictions:
            success = await PredictionHistoryService.delete_by_id(session, pred.id)
            if success:
                deleted_count += 1
        
        await session.commit()
        
        if deleted_count > 0:
            await callback.message.answer(
                f"✅ *История предсказаний очищена*\n\n"
                f"Удалено записей: {deleted_count}\n\n"
                f"Теперь ваша история предсказаний пуста.",
                parse_mode="Markdown"
            )
        else:
            await callback.message.answer(
                "📭 *Нечего удалять*\n\n"
                "У вас нет записей в истории предсказаний.",
                parse_mode="Markdown"
            )
    
    await callback.answer()


@router.callback_query(lambda c: c.data == "predictions_clear_no")
async def handle_predictions_clear_no(callback: CallbackQuery):
    """Отмена очистки истории"""
    await callback.message.answer(
        "❌ *Очистка истории отменена*\n\n"
        "Ваши данные сохранены.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(Command("prediction_stats"))
async def cmd_prediction_stats(message: Message):
    """Статистика предсказаний (админ/консультант)"""
    user_id = message.from_user.id
    
    # Проверка прав (можно добавить позже)
    # if not is_consultant(user_id):
    #     await message.answer("⛔️ У вас нет прав для просмотра статистики.")
    #     return
    
    async with get_session_maker()() as session:
        stats = await PredictionHistoryService.get_global_statistics(session)
        
        stats_text = f"""
🌍 *Глобальная статистика предсказаний*

*Всего предсказаний:* {stats['total']}
*Уникальных пользователей:* {stats['unique_users']}
*За сегодня:* {stats['today_count']}

*Распределение по типам:*
"""
        for pred_type, count in stats["by_type"].items():
            percentage = (count / stats["total"]) * 100 if stats["total"] > 0 else 0
            type_name = pred_type.replace("_", " ").title()
            stats_text += f"• *{type_name}*: {count} ({percentage:.1f}%)\n"
        
        stats_text += f"\n*Самый популярный тип:* {stats['popular_type'].replace('_', ' ').title()} ({stats['popular_type_count']} раз)"
        
        await message.answer(stats_text, parse_mode="Markdown")