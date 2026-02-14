"""
Обработчики для работы с картами Таро
"""

import logging
import random
import json
from pathlib import Path
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.prediction_history_service import PredictionHistoryService
from bot.models.prediction_history import PredictionType
from bot.database.engine import get_session_maker

router = Router()
log = logging.getLogger(__name__)


def load_tarot_deck():
    """Загружает колоду Таро из JSON файла."""
    deck_path = Path(__file__).parent.parent.parent / "data" / "tarot_deck.json"
    try:
        with open(deck_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("cards", [])
    except Exception as e:
        log.error(f"Ошибка загрузки колоды Таро: {e}")
        # Возвращаем пустой список как fallback
        return []


def get_random_cards(cards, count=1, allow_repeats=False):
    """Возвращает случайные карты из колоды."""
    if not cards:
        return []
    
    if allow_repeats:
        selected = random.choices(cards, k=count)
    else:
        if count > len(cards):
            count = len(cards)
        selected = random.sample(cards, count)
    
    return selected


# Состояния для расклада
class TarotReading(StatesGroup):
    choosing_spread = State()  # Выбор расклада
    waiting_for_question = State()  # Ожидание вопроса


@router.message(Command("tarot"))
async def cmd_tarot(message: Message, state: FSMContext):
    """Команда /tarot - начало работы с Таро"""
    log.info(f"Received /tarot command from {message.from_user.id}")
    await state.set_state(TarotReading.choosing_spread)
    
    text = """
🃏 *Карты Таро*

Выберите тип расклада:

*1. Одна карта* — Быстрый ответ на вопрос
*2. Три карты* — Прошлое, Настоящее, Будущее
*3. Кельтский крест* — Подробный анализ ситуации
*4. Любовный расклад* — Вопросы отношений
*5. Финансовый расклад* — Деньги и карьера

Или задайте свой вопрос, и я подберу подходящий расклад.
"""
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="Одна карта", callback_data="tarot_one"))
    builder.row(types.InlineKeyboardButton(text="Три карты", callback_data="tarot_three"))
    builder.row(types.InlineKeyboardButton(text="Кельтский крест", callback_data="tarot_cross"))
    builder.row(types.InlineKeyboardButton(text="Любовный расклад", callback_data="tarot_love"))
    builder.row(types.InlineKeyboardButton(text="Финансовый расклад", callback_data="tarot_finance"))
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("tarot_"))
async def process_tarot_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора расклада"""
    spread_type = callback.data
    
    spread_names = {
        "tarot_one": "Одна карта",
        "tarot_three": "Три карты",
        "tarot_cross": "Кельтский крест",
        "tarot_love": "Любовный расклад",
        "tarot_finance": "Финансовый расклад"
    }
    
    spread_name = spread_names.get(spread_type, "Неизвестный расклад")
    
    await state.update_data(spread_type=spread_type, spread_name=spread_name)
    await state.set_state(TarotReading.waiting_for_question)
    
    text = f"""
Вы выбрали: *{spread_name}*

Теперь сформулируйте свой вопрос или ситуацию, которую хотите прояснить.

*Примеры вопросов:*
• "Что ждёт меня на этой неделе?"
• "Как улучшить отношения с партнёром?"
• "Какие возможности для карьеры откроются?"
• "Какой выбор будет правильным?"

Напишите ваш вопрос:
"""
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@router.message(TarotReading.waiting_for_question)
async def process_question(message: Message, state: FSMContext):
    """Обработка вопроса пользователя и генерация расклада"""
    question = message.text
    data = await state.get_data()
    spread_name = data.get("spread_name", "Расклад")
    spread_type = data.get("spread_type", "tarot_one")
    
    # Загружаем колоду
    deck = load_tarot_deck()
    if not deck:
        await message.answer("❌ Колода Таро временно недоступна. Попробуйте позже.")
        await state.clear()
        return
    
    # Определяем количество карт в зависимости от расклада
    spread_configs = {
        "tarot_one": 1,
        "tarot_three": 3,
        "tarot_cross": 10,  # Кельтский крест обычно 10 карт
        "tarot_love": 5,    # Любовный расклад
        "tarot_finance": 5  # Финансовый расклад
    }
    
    card_count = spread_configs.get(spread_type, 1)
    
    # Выбираем случайные карты (без повторов)
    selected_cards = get_random_cards(deck, card_count, allow_repeats=False)
    
    # Генерируем текст расклада
    reading_parts = [f"🔮 *{spread_name}*", f"*Вопрос:* {question}", "", "*Результат расклада:*", ""]
    card_details = []  # Для сохранения в истории
    
    for i, card in enumerate(selected_cards, 1):
        # Случайное положение (прямое или перевёрнутое)
        is_reversed = random.choice([True, False])
        position = "Перевёрнутое" if is_reversed else "Прямое"
        meaning = card["meaning_reversed"] if is_reversed else card["meaning_upright"]
        
        # Эмодзи для карты
        emoji = "🃏" if "Шут" in card["name"] else "🎴"
        
        reading_parts.append(f"**Карта {i}: {emoji} {card['name']} ({card['name_en']})**")
        reading_parts.append(f"*{position} положение:* {meaning}")
        reading_parts.append("")
        
        # Сохраняем детали карты для истории
        card_details.append({
            "card_number": i,
            "name": card["name"],
            "name_en": card["name_en"],
            "is_reversed": is_reversed,
            "position": position,
            "meaning": meaning,
            "emoji": emoji
        })
    
    # Общая интерпретация
    reading_parts.append("---")
    reading_parts.append("✨ *Общий совет:* Слушайте своё сердце и доверяйте своей интуиции.")
    
    reading_text = "\n".join(reading_parts)
    
    # Сохраняем в историю предсказаний
    try:
        async with get_session_maker()() as session:
            await PredictionHistoryService.create_prediction(
                session=session,
                user_id=message.from_user.id,
                prediction_type=PredictionType.TAROT,
                subtype=spread_type,
                details=card_details,
                result_text=reading_text,
                user_message=question,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
            )
    except Exception as e:
        log.error(f"Ошибка при сохранении истории предсказаний Таро: {e}")
        # Продолжаем выполнение, не прерывая работу бота
    
    await state.clear()
    await message.answer(reading_text, parse_mode="Markdown")
    
    # Предложить сохранить расклад
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💾 Сохранить расклад", callback_data="save_reading"))
    builder.row(types.InlineKeyboardButton(text="🔄 Новый расклад", callback_data="new_reading"))
    
    await message.answer("Что дальше?", reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data == "save_reading")
async def handle_save_reading(callback: CallbackQuery):
    """Сохранение расклада (заглушка)"""
    await callback.answer("💾 Функция сохранения расклада скоро появится!", show_alert=True)


@router.callback_query(lambda c: c.data == "new_reading")
async def handle_new_reading(callback: CallbackQuery, state: FSMContext):
    """Начать новый расклад"""
    await state.clear()
    await callback.answer()
    # Показываем меню выбора расклада
    await cmd_tarot(callback.message, state)


# Обработчик текстовой кнопки "Карты Таро" (для совместимости)
@router.message(lambda m: m.text and "таро" in m.text.lower())
async def handle_tarot_text(message: Message, state: FSMContext):
    """Обработка текстового упоминания Таро"""
    await cmd_tarot(message, state)