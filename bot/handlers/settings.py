"""
Обработчики для настроек пользователя и уведомлений.
"""

import logging
from datetime import time
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.user_settings import UserSettingsService
from bot.services.daily_content import DailyContentService

router = Router()
log = logging.getLogger(__name__)


# Состояния для настройки уведомлений
class NotificationSettings(StatesGroup):
    choosing_time = State()
    choosing_modules = State()


@router.message(Command("settings"))
async def cmd_settings(message: Message, session_maker=None):
    """Команда /settings — настройки пользователя."""
    if not session_maker:
        await message.answer(
            "⚙️ *Настройки временно недоступны*\n"
            "База данных не подключена.",
            parse_mode="Markdown"
        )
        return
    
    user_id = message.from_user.id
    
    async with session_maker() as session:
        settings = await UserSettingsService.get_or_create(session, user_id)
        stats = await UserSettingsService.get_user_stats(session, user_id)
    
    # Формируем ответ
    response = "⚙️ *Ваши настройки*\n\n"
    
    response += f"*Язык:* {settings.preferred_language}\n"
    response += f"*Избранные модули:* {', '.join(settings.get_favorite_modules_list()) or 'нет'}\n\n"
    
    response += "*Уведомления:*\n"
    response += f"• Ежедневные уведомления: {'✅ включены' if settings.enable_daily_notifications else '❌ выключены'}\n"
    if settings.enable_daily_notifications:
        notification_time = settings.notification_time.strftime("%H:%M")
        response += f"• Время уведомлений: {notification_time}\n"
        response += f"• Руна дня: {'✅' if settings.notify_rune_of_day else '❌'}\n"
        response += f"• Аффирмация дня: {'✅' if settings.notify_affirmation_of_day else '❌'}\n"
        response += f"• Гороскоп дня: {'✅' if settings.notify_horoscope_daily else '❌'}\n"
        response += f"• Карта Таро дня: {'✅' if settings.notify_tarot_card_of_day else '❌'}\n"
        response += f"• Напоминание о медитации: {'✅' if settings.notify_meditation_reminder else '❌'}\n\n"
    
    response += "*Статистика:*\n"
    response += f"• Консультаций с AI: {stats.get('total_consultations', 0)}\n"
    response += f"• Загруженных файлов: {stats.get('total_files_uploaded', 0)}\n"
    response += f"• Последняя активность: {stats.get('last_active', 'неизвестно')}\n"
    
    # Клавиатура настроек
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications"),
        InlineKeyboardButton(text="⭐ Избранное", callback_data="settings_favorites"),
    )
    builder.row(
        InlineKeyboardButton(text="🧘 Медитации", callback_data="settings_meditation"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="settings_stats"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Тест уведомлений", callback_data="settings_test_notification"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="settings_close"),
    )
    
    await message.answer(response, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data.startswith("settings_"))
async def process_settings_callback(callback: CallbackQuery, state: FSMContext, session_maker=None):
    """Обработка колбэков настроек."""
    action = callback.data
    
    if action == "settings_close":
        await callback.message.delete()
        await callback.answer()
        return
    
    if not session_maker:
        await callback.answer("База данных недоступна", show_alert=True)
        return
    
    user_id = callback.from_user.id
    
    if action == "settings_notifications":
        # Показать настройки уведомлений
        async with session_maker() as session:
            settings = await UserSettingsService.get_or_create(session, user_id)
        
        builder = InlineKeyboardBuilder()
        
        # Переключение ежедневных уведомлений
        toggle_text = "❌ Выключить" if settings.enable_daily_notifications else "✅ Включить"
        builder.row(InlineKeyboardButton(
            text=toggle_text, 
            callback_data=f"notifications_toggle_{'off' if settings.enable_daily_notifications else 'on'}"
        ))
        
        if settings.enable_daily_notifications:
            builder.row(InlineKeyboardButton(
                text="⏰ Изменить время", 
                callback_data="notifications_change_time"
            ))
            
            # Переключение отдельных уведомлений
            builder.row(InlineKeyboardButton(
                text=f"Руна дня: {'✅' if settings.notify_rune_of_day else '❌'}", 
                callback_data=f"notifications_toggle_rune_{'off' if settings.notify_rune_of_day else 'on'}"
            ))
            builder.row(InlineKeyboardButton(
                text=f"Аффирмация: {'✅' if settings.notify_affirmation_of_day else '❌'}", 
                callback_data=f"notifications_toggle_affirmation_{'off' if settings.notify_affirmation_of_day else 'on'}"
            ))
            builder.row(InlineKeyboardButton(
                text=f"Гороскоп: {'✅' if settings.notify_horoscope_daily else '❌'}", 
                callback_data=f"notifications_toggle_horoscope_{'off' if settings.notify_horoscope_daily else 'on'}"
            ))
            builder.row(InlineKeyboardButton(
                text=f"Карта Таро: {'✅' if settings.notify_tarot_card_of_day else '❌'}", 
                callback_data=f"notifications_toggle_tarot_{'off' if settings.notify_tarot_card_of_day else 'on'}"
            ))
            builder.row(InlineKeyboardButton(
                text=f"Медитация: {'✅' if settings.notify_meditation_reminder else '❌'}", 
                callback_data=f"notifications_toggle_meditation_{'off' if settings.notify_meditation_reminder else 'on'}"
            ))
        
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back"))
        
        text = "🔔 *Настройки уведомлений*\n\n"
        if settings.enable_daily_notifications:
            notification_time = settings.notification_time.strftime("%H:%M")
            text += f"Уведомления приходят ежедневно в *{notification_time}* по вашему времени.\n"
        else:
            text += "Ежедневные уведомления выключены.\n"
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
        await callback.answer()
    
    elif action == "settings_favorites":
        # Настройка избранных модулей
        async with session_maker() as session:
            settings = await UserSettingsService.get_or_create(session, user_id)
        
        favorite_modules = settings.get_favorite_modules_list()
        
        builder = InlineKeyboardBuilder()
        
        modules = [
            ("Таро", "tarot"),
            ("Нумерология", "numerology"),
            ("Гороскоп", "horoscope"),
            ("Руны", "runes"),
            ("Сонник", "dream"),
            ("Астрология", "astrology"),
            ("Медитации", "meditation"),
            ("AI-консультации", "ask"),
        ]
        
        for display_name, module_name in modules:
            is_favorite = module_name in favorite_modules
            button_text = f"{'⭐' if is_favorite else '○'} {display_name}"
            builder.row(InlineKeyboardButton(
                text=button_text,
                callback_data=f"favorite_toggle_{module_name}"
            ))
        
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back"))
        
        text = "⭐ *Избранные модули*\n\n"
        text += "Добавьте модули в избранное для быстрого доступа из главного меню.\n"
        text += f"Сейчас в избранном: {len(favorite_modules)} модулей."
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
        await callback.answer()
    
    elif action == "settings_meditation":
        # Настройки медитаций
        text = "🧘 *Настройки медитаций*\n\n"
        text += "Здесь вы можете настроить напоминания о медитациях и выбрать любимые практики.\n\n"
        text += "Функция в разработке. Скоро будет доступна!"
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back"))
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
        await callback.answer()
    
    elif action == "settings_stats":
        # Подробная статистика
        async with session_maker() as session:
            stats = await UserSettingsService.get_user_stats(session, user_id)
        
        text = "📊 *Ваша статистика*\n\n"
        text += f"• Консультаций с AI: {stats.get('total_consultations', 0)}\n"
        text += f"• Загруженных файлов: {stats.get('total_files_uploaded', 0)}\n"
        text += f"• Последняя активность: {stats.get('last_active', 'недавно')}\n"
        text += f"• Время уведомлений: {stats.get('notification_time', 'не настроено')}\n"
        text += f"• Любимые модули: {', '.join(stats.get('favorite_modules', [])) or 'нет'}\n\n"
        text += "_Статистика помогает нам улучшать бота для вас._"
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="settings_stats"))
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="settings_back"))
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
        await callback.answer()
    
    elif action == "settings_test_notification":
        # Тестовое уведомление
        notification_text = DailyContentService.generate_daily_notification(
            user_id=user_id,
            include_rune=True,
            include_affirmation=True,
            include_tarot=True,
            include_zodiac=True,
            include_meditation=True,
        )
        
        await callback.message.answer(notification_text, parse_mode="Markdown")
        await callback.answer("Тестовое уведомление отправлено!")
    
    elif action == "settings_back":
        # Возврат к основным настройкам
        await cmd_settings(callback.message, session_maker)
        await callback.answer()
    
    else:
        await callback.answer("Действие не распознано")


@router.callback_query(lambda c: c.data.startswith("notifications_"))
async def process_notifications_callback(callback: CallbackQuery, session_maker=None):
    """Обработка колбэков уведомлений."""
    if not session_maker:
        await callback.answer("База данных недоступна", show_alert=True)
        return
    
    action = callback.data
    user_id = callback.from_user.id
    
    async with session_maker() as session:
        settings = await UserSettingsService.get_or_create(session, user_id)
        
        if action.startswith("notifications_toggle_"):
            toggle_type = action.split("_")[2]  # on/off или rune_on и т.д.
            
            if toggle_type in ["on", "off"]:
                # Включение/выключение всех уведомлений
                settings.enable_daily_notifications = (toggle_type == "on")
                if toggle_type == "on":
                    # Включаем по умолчанию руну и аффирмацию
                    settings.notify_rune_of_day = True
                    settings.notify_affirmation_of_day = True
            
            elif toggle_type.startswith("rune"):
                state = action.split("_")[3]
                settings.notify_rune_of_day = (state == "on")
            
            elif toggle_type.startswith("affirmation"):
                state = action.split("_")[3]
                settings.notify_affirmation_of_day = (state == "on")
            
            elif toggle_type.startswith("horoscope"):
                state = action.split("_")[3]
                settings.notify_horoscope_daily = (state == "on")
            
            elif toggle_type.startswith("tarot"):
                state = action.split("_")[3]
                settings.notify_tarot_card_of_day = (state == "on")
            
            elif toggle_type.startswith("meditation"):
                state = action.split("_")[3]
                settings.notify_meditation_reminder = (state == "on")
            
            await session.commit()
            await callback.answer("Настройки обновлены!")
            
            # Обновляем интерфейс
            await process_settings_callback(
                CallbackQuery(
                    id=callback.id,
                    from_user=callback.from_user,
                    chat_instance=callback.chat_instance,
                    message=callback.message,
                    data="settings_notifications"
                ),
                callback.message.bot,
                session_maker
            )
        
        elif action == "notifications_change_time":
            await callback.message.answer(
                "⏰ *Укажите время уведомлений*\n\n"
                "Отправьте время в формате *ЧЧ:ММ* (например, 09:00 или 21:30).\n"
                "Уведомления будут приходить ежедневно в это время.",
                parse_mode="Markdown"
            )
            await callback.answer()
            # Здесь нужно перейти в состояние ожидания времени, но упростим — пропустим
            # Реализуем в следующей итерации


@router.callback_query(lambda c: c.data.startswith("favorite_toggle_"))
async def process_favorite_callback(callback: CallbackQuery, session_maker=None):
    """Обработка колбэков избранных модулей."""
    if not session_maker:
        await callback.answer("База данных недоступна", show_alert=True)
        return
    
    module_name = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    async with session_maker() as session:
        settings = await UserSettingsService.get_or_create(session, user_id)
        
        if module_name in settings.get_favorite_modules_list():
            settings.remove_favorite_module(module_name)
            await session.commit()
            await callback.answer(f"Модуль удалён из избранного")
        else:
            settings.add_favorite_module(module_name)
            await session.commit()
            await callback.answer(f"Модуль добавлен в избранное")
        
        # Обновляем интерфейс
        await process_settings_callback(
            CallbackQuery(
                id=callback.id,
                from_user=callback.from_user,
                chat_instance=callback.chat_instance,
                message=callback.message,
                data="settings_favorites"
            ),
            callback.message.bot,
            session_maker
        )


@router.message(Command("test_notification"))
async def cmd_test_notification(message: Message):
    """Тестовая команда для проверки уведомлений."""
    notification_text = DailyContentService.generate_daily_notification(
        user_id=message.from_user.id,
        include_rune=True,
        include_affirmation=True,
        include_tarot=True,
        include_zodiac=True,
        include_meditation=True,
    )
    
    await message.answer(notification_text, parse_mode="Markdown")