"""
Модуль астрологии: натальная карта, транзиты, совместимость.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

# Вспомогательные функции
def validate_date(date_str: str) -> bool:
    """Проверка формата даты ДД.ММ.ГГГГ."""
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

# Роутер
astrology_router = Router()
router = astrology_router

# Состояния FSM
class AstrologyStates(StatesGroup):
    waiting_birth_date = State()
    waiting_birth_time = State()
    waiting_birth_place = State()
    waiting_question = State()

# Кнопки
def get_astrology_main_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню астрологии."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌌 Натальная карта", callback_data="astrology_natal"),
        InlineKeyboardButton(text="🔄 Транзиты", callback_data="astrology_transits"),
    )
    builder.row(
        InlineKeyboardButton(text="💞 Совместимость", callback_data="astrology_compatibility"),
        InlineKeyboardButton(text="📅 Гороскоп на день", callback_data="astrology_daily"),
    )
    builder.row(
        InlineKeyboardButton(text="📚 Обучение астрологии", callback_data="astrology_learn"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="astrology_back"),
    )
    return builder.as_markup()


# Команда /astrology и обработка текстовой кнопки
@astrology_router.message(Command("astrology"))
@astrology_router.message(F.text.contains("Астрология"))
async def cmd_astrology(message: Message, state: FSMContext):
    """Команда /astrology - главное меню астрологии."""
    await state.clear()
    await message.answer(
        "🌌 *Пространство астрологии*\n\n"
        "Выберите раздел:",
        reply_markup=get_astrology_main_keyboard(),
        parse_mode="Markdown"
    )

# Обработчики
@astrology_router.message(F.text.contains("астролог"))
@astrology_router.message(F.text.contains("Астролог"))
@astrology_router.message(F.text == "🌌 Астрология")
async def cmd_astrology(message: Message, state: FSMContext):
    """Команда /astrology или упоминание астрологии."""
    await state.clear()
    await message.answer(
        "🌌 *Астрологический раздел*\n\n"
        "Выберите интересующий вас вариант:",
        reply_markup=get_astrology_main_keyboard(),
        parse_mode="Markdown"
    )

@astrology_router.callback_query(F.data == "astrology_natal")
async def astrology_natal_start(callback: CallbackQuery, state: FSMContext):
    """Начало расчёта натальной карты."""
    await callback.message.edit_text(
        "🌠 *Натальная карта*\n\n"
        "Для построения натальной карты мне нужны ваши данные:\n"
        "1. Дата рождения (ДД.ММ.ГГГГ)\n"
        "2. Время рождения (ЧЧ:ММ, по местному времени)\n"
        "3. Место рождения (город, страна)\n\n"
        "Введите *дату рождения* (например, 15.09.1990):",
        parse_mode="Markdown"
    )
    await state.set_state(AstrologyStates.waiting_birth_date)

@astrology_router.message(AstrologyStates.waiting_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    """Обработка даты рождения."""
    date_str = message.text.strip()
    if not validate_date(date_str):
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 15.09.1990). Попробуйте снова:")
        return
    
    await state.update_data(birth_date=date_str)
    await message.answer(
        "✅ Дата принята.\n\n"
        "Теперь введите *время рождения* (например, 14:30):"
    )
    await state.set_state(AstrologyStates.waiting_birth_time)

@astrology_router.message(AstrologyStates.waiting_birth_time)
async def process_birth_time(message: Message, state: FSMContext):
    """Обработка времени рождения."""
    time_str = message.text.strip()
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30). Попробуйте снова:")
        return
    
    await state.update_data(birth_time=time_str)
    await message.answer(
        "✅ Время принято.\n\n"
        "Теперь введите *место рождения* (город, страна):"
    )
    await state.set_state(AstrologyStates.waiting_birth_place)

@astrology_router.message(AstrologyStates.waiting_birth_place)
async def process_birth_place(message: Message, state: FSMContext):
    """Обработка места рождения."""
    place = message.text.strip()
    if len(place) < 2:
        await message.answer("❌ Место слишком короткое. Введите город и страну (например, Москва, Россия):")
        return
    
    data = await state.get_data()
    birth_date = data.get('birth_date')
    birth_time = data.get('birth_time')
    
    # Здесь будет интеграция с астрологическим API (например, Swiss Ephemeris)
    # Пока заглушка
    await message.answer(
        f"🌌 *Ваша натальная карта*\n\n"
        f"📅 Дата: {birth_date}\n"
        f"⏰ Время: {birth_time}\n"
        f"📍 Место: {place}\n\n"
        f"*Солнце*: в знаке Тельца (устойчивость, практичность)\n"
        f"*Луна*: в Раке (эмоциональность, интуиция)\n"
        f"*Асцендент*: в Весах (гармония, дипломатия)\n"
        f"*Меркурий*: в Близнецах (любознательность, общительность)\n"
        f"*Венера*: в Тельце (чувственность, верность)\n"
        f"*Марс*: в Овне (энергия, инициатива)\n\n"
        f"*Рекомендации*: развивайте практические навыки, доверяйте интуиции, ищите баланс в отношениях.\n\n"
        f"💾 Вы можете сохранить этот расклад в профиле.",
        parse_mode="Markdown"
    )
    await state.clear()

@astrology_router.callback_query(F.data == "astrology_transits")
async def astrology_transits(callback: CallbackQuery):
    """Транзиты планет."""
    await callback.message.edit_text(
        "🔄 *Транзиты планет*\n\n"
        "Транзиты показывают, как текущее положение планет влияет на вашу натальную карту.\n\n"
        "Для анализа транзитов мне нужна ваша натальная карта (сохраните её через раздел «Натальная карта»).\n\n"
        "Сейчас доступны:\n"
        "• Солнце в Рыбах (до 20 марта) — время интуиции, творчества.\n"
        "• Меркурий в Водолее (до 5 марта) — нестандартное мышление, инновации.\n"
        "• Венера в Козероге (до 10 марта) — серьёзность в отношениях, карьерный рост.\n\n"
        "📅 *Совет*: планируйте важные переговоры на первую неделю марта.",
        parse_mode="Markdown"
    )

@astrology_router.callback_query(F.data == "astrology_compatibility")
async def astrology_compatibility(callback: CallbackQuery):
    """Совместимость по натальным картам."""
    await callback.message.edit_text(
        "💞 *Совместимость по натальным картам*\n\n"
        "Для анализа совместимости нужны данные двух людей:\n"
        "1. Дата, время, место рождения первого человека.\n"
        "2. Дата, время, место рождения второго человека.\n\n"
        "Сейчас функция в разработке. Скоро появится! 🚀\n\n"
        "А пока можете попробовать совместимость по знакам зодиака через /horoscope.",
        parse_mode="Markdown"
    )

@astrology_router.callback_query(F.data == "astrology_daily")
async def astrology_daily(callback: CallbackQuery):
    """Гороскоп на день с астрологической детализацией."""
    await callback.message.edit_text(
        "📅 *Астрологический гороскоп на день*\n\n"
        "Сегодняшние аспекты:\n"
        "• Луна в Скорпионе — глубокие эмоции, трансформация.\n"
        "• Марс квадрат Уран — неожиданные события, будьте осторожны.\n"
        "• Венера трин Нептун — романтическое вдохновение, творчество.\n\n"
        "🧘 *Рекомендации*: уделите время самоанализу, избегайте резких решений, доверяйте интуиции в отношениях.",
        parse_mode="Markdown"
    )

@astrology_router.callback_query(F.data == "astrology_learn")
async def astrology_learn(callback: CallbackQuery):
    """Обучение астрологии."""
    await callback.message.edit_text(
        "📚 *Обучение астрологии*\n\n"
        "Ресурсы для начинающих:\n"
        "• **Книги**: «Астрология для начинающих» Джоанны Вулфолк, «Планеты и ты».\n"
        "• **Курсы**: AstroSchool, Астрологический институт.\n"
        "• **Программы**: Solar Fire, Astro.com для расчётов.\n"
        "• **Практика**: ведите дневник транзитов, анализируйте карты друзей.\n\n"
        "🌌 *Совет*: начните с изучения своих планет, затем переходите к синастрии.",
        parse_mode="Markdown"
    )

@astrology_router.callback_query(F.data == "astrology_back")
async def astrology_back(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    await callback.message.edit_text(
        "🔙 Возвращаемся в главное меню.\n\n"
        "Используйте /help для списка команд.",
        parse_mode="Markdown"
    )