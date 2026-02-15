"""
Модуль медитаций, дыхательных практик и аффирмаций.
"""

import logging
from datetime import datetime
from typing import List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

# Роутер
meditation_router = Router()
router = meditation_router

# Состояния FSM
class MeditationStates(StatesGroup):
    waiting_mood = State()
    waiting_duration = State()

# Кнопки
def get_meditation_main_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню медитаций."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🧘 Медитация", callback_data="meditation_guided"),
        InlineKeyboardButton(text="🌬️ Дыхание", callback_data="meditation_breathing"),
    )
    builder.row(
        InlineKeyboardButton(text="💭 Аффирмации", callback_data="meditation_affirmations"),
        InlineKeyboardButton(text="🎵 Звуки", callback_data="meditation_sounds"),
    )
    builder.row(
        InlineKeyboardButton(text="📅 Ежедневная практика", callback_data="meditation_daily"),
        InlineKeyboardButton(text="📚 Обучение", callback_data="meditation_learn"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="meditation_back"),
    )
    return builder.as_markup()

# Обработчики
@meditation_router.message(Command("meditation"))
@meditation_router.message(F.text.contains("медитац"))
@meditation_router.message(F.text.contains("Медитац"))
@meditation_router.message(F.text == "🧘 Медитация")
async def cmd_meditation(message: Message, state: FSMContext):
    """Команда /meditation или упоминание медитации."""
    await state.clear()
    await message.answer(
        "🧘 *Пространство медитаций*\n\n"
        "Выберите тип практики:",
        reply_markup=get_meditation_main_keyboard(),
        parse_mode="Markdown"
    )

@meditation_router.callback_query(F.data == "meditation_guided")
async def meditation_guided(callback: CallbackQuery):
    """Направляемая медитация."""
    await callback.message.edit_text(
        "🧘 *Направляемая медитация «Расслабление и осознанность»*\n\n"
        "1. Сядьте удобно, закройте глаза.\n"
        "2. Сделайте три глубоких вдоха и выдоха.\n"
        "3. Сосредоточьтесь на дыхании — вдох на 4 счёта, задержка на 2, выдох на 6.\n"
        "4. Почувствуйте, как напряжение уходит с каждым выдохом.\n"
        "5. Представьте себе тёплый свет, который наполняет вас спокойствием.\n"
        "6. Побудьте в этом состоянии 5–10 минут.\n\n"
        "✨ *Совет:* используйте эту медитацию утром или перед сном.",
        parse_mode="Markdown"
    )

@meditation_router.callback_query(F.data == "meditation_breathing")
async def meditation_breathing(callback: CallbackQuery):
    """Дыхательные упражнения."""
    await callback.message.edit_text(
        "🌬️ *Дыхательная практика «4‑7‑8»*\n\n"
        "Техника для снятия стресса и улучшения сна:\n"
        "1. Вдох через нос на 4 счёта.\n"
        "2. Задержка дыхания на 7 счётов.\n"
        "3. Медленный выдох через рот на 8 счётов.\n\n"
        "Повторите 4 раза.\n\n"
        "🎯 *Эффект:* успокаивает нервную систему, снижает тревожность.",
        parse_mode="Markdown"
    )

@meditation_router.callback_query(F.data == "meditation_affirmations")
async def meditation_affirmations(callback: CallbackQuery):
    """Аффирмации на сегодня."""
    affirmations = [
        "Я доверяю себе и своей интуиции.",
        "Я открыт для изобилия и возможностей.",
        "Я создаю гармонию внутри и вокруг себя.",
        "Я отпускаю то, что мне не служит.",
        "Я расту и развиваюсь каждый день.",
        "Я достоин любви и уважения.",
        "Я привлекаю позитивные события.",
        "Я нахожусь в потоке жизни.",
    ]
    today_index = datetime.now().day % len(affirmations)
    selected = affirmations[today_index]
    
    await callback.message.edit_text(
        "💭 *Аффирмация дня*\n\n"
        f"**{selected}**\n\n"
        "*Как работать с аффирмациями:*\n"
        "1. Произнесите вслух 3 раза утром.\n"
        "2. Запишите в дневник.\n"
        "3. Повторяйте в течение дня, когда чувствуете сомнения.\n\n"
        "✨ *Эффект:* перепрограммирование подсознания на успех.",
        parse_mode="Markdown"
    )

@meditation_router.callback_query(F.data == "meditation_sounds")
async def meditation_sounds(callback: CallbackQuery):
    """Звуки для медитации."""
    await callback.message.edit_text(
        "🎵 *Звуковая терапия*\n\n"
        "Рекомендуемые частоты:\n"
        "• **528 Гц** — репарация ДНК, исцеление.\n"
        "• **432 Гц** — гармония с природой.\n"
        "• **639 Гц** — гармонизация отношений.\n"
        "• **741 Гц** — очищение, пробуждение интуиции.\n\n"
        "🎧 *Совет:* слушайте в наушниках 15–30 минут в день.",
        parse_mode="Markdown"
    )

@meditation_router.callback_query(F.data == "meditation_daily")
async def meditation_daily(callback: CallbackQuery):
    """Ежедневная практика."""
    await callback.message.edit_text(
        "📅 *Ежедневная практика «Утро силы»*\n\n"
        "1. **Пробуждение (5 мин):** лёгкая растяжка, благодарность за новый день.\n"
        "2. **Дыхание (3 мин):** техника 4‑7‑8.\n"
        "3. **Медитация (10 мин):** направляемая медитация на намерение.\n"
        "4. **Аффирмации (2 мин):** повторите аффирмацию дня.\n"
        "5. **Планирование (5 мин):** запишите 3 главные задачи на день.\n\n"
        "🎯 *Результат:* повышенная продуктивность, ясность ума, спокойствие.",
        parse_mode="Markdown"
    )

@meditation_router.callback_query(F.data == "meditation_learn")
async def meditation_learn(callback: CallbackQuery):
    """Обучение медитации."""
    await callback.message.edit_text(
        "📚 *Обучение медитации*\n\n"
        "Книги:\n"
        "• «Сила настоящего» Экхарт Толле\n"
        "• «Осознанность» Марк Уильямс\n"
        "• «Медитация и осознанность» Энди Паддикомб\n\n"
        "Приложения:\n"
        "• Headspace (русская версия)\n"
        "• Calm\n"
        "• Insight Timer\n\n"
        "Курсы:\n"
        "• «Медитация для начинающих» на Coursera\n"
        "• «Практики осознанности» от Mindvalley\n\n"
        "🌱 *Совет:* начинайте с 5 минут в день, постепенно увеличивая время.",
        parse_mode="Markdown"
    )

@meditation_router.callback_query(F.data == "meditation_back")
async def meditation_back(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()
    await callback.message.edit_text(
        "🔙 Возвращаемся в главное меню.\n\n"
        "Используйте /help для списка команд.",
        parse_mode="Markdown"
    )