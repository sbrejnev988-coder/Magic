"""
Обработчики для гадания на рунах
"""

import logging
import random
from aiogram import Router, types, F
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


# Состояния для гадания на рунах
class RunesDivination(StatesGroup):
    choosing_spread = State()  # Выбор расклада
    waiting_for_question = State()  # Ожидание вопроса


# Старшие руны (24 руны старшего футарка)
RUNES = [
    {"name": "ᚠ Fehu", "meaning": "Скот, богатство, собственность"},
    {"name": "ᚢ Uruz", "meaning": "Зубр, сила, здоровье"},
    {"name": "ᚦ Thurisaz", "meaning": "Тор, защита, конфликт"},
    {"name": "ᚫ Ansuz", "meaning": "Бог, сообщение, мудрость"},
    {"name": "ᚱ Raidho", "meaning": "Поездка, путешествие, движение"},
    {"name": "ᚲ Kenaz", "meaning": "Факел, знание, творчество"},
    {"name": "ᚷ Gebo", "meaning": "Дар, партнёрство, обмен"},
    {"name": "ᚹ Wunjo", "meaning": "Радость, благополучие, успех"},
    {"name": "ᚺ Hagalaz", "meaning": "Град, разрушение, стихия"},
    {"name": "ᚾ Nauthiz", "meaning": "Нужда, сопротивление, вызов"},
    {"name": "ᛁ Isa", "meaning": "Лёд, застой, остановка"},
    {"name": "ᛃ Jera", "meaning": "Урожай, цикл, вознаграждение"},
    {"name": "ᛇ Eihwaz", "meaning": "Тис, защита, переход"},
    {"name": "ᛈ Perthro", "meaning": "Тайна, судьба, неведомое"},
    {"name": "ᛉ Algiz", "meaning": "Лось, защита, бдительность"},
    {"name": "ᛋ Sowilo", "meaning": "Солнце, победа, энергия"},
    {"name": "ᛏ Tiwaz", "meaning": "Тюр, справедливость, жертва"},
    {"name": "ᛒ Berkano", "meaning": "Берёза, рост, плодородие"},
    {"name": "ᛖ Ehwaz", "meaning": "Лошадь, движение, прогресс"},
    {"name": "ᛗ Mannaz", "meaning": "Человек, общество, сотрудничество"},
    {"name": "ᛚ Laguz", "meaning": "Вода, интуиция, поток"},
    {"name": "ᛝ Ingwaz", "meaning": "Инг, потенциал, внутренний рост"},
    {"name": "ᛟ Othala", "meaning": "Наследие, дом, традиции"},
    {"name": "ᛞ Dagaz", "meaning": "День, прорыв, трансформация"},
]


@router.message(Command("runes"))
async def cmd_runes(message: Message, state: FSMContext):
    """Команда /runes - начало гадания на рунах"""
    await state.set_state(RunesDivination.choosing_spread)
    
    text = """
ᚱ *Руны — древнее гадание*

Руны — это алфавит древних германцев, каждая руна имеет магическое значение.

*Выберите расклад:*

*1. Одна руна* — Ответ на конкретный вопрос
*2. Три руны* — Прошлое, Настоящее, Будущее
*3. Руна дня* — Совет на сегодня
*4. Руна ситуации* — Анализ текущей ситуации
*5. Руна отношения* — Вопросы любви и партнёрства

Или задайте свой вопрос, и я выберу подходящий расклад.
"""
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="ᚠ Одна руна", callback_data="runes_one"))
    builder.row(types.InlineKeyboardButton(text="ᚠᚢᚦ Три руны", callback_data="runes_three"))
    builder.row(types.InlineKeyboardButton(text="ᛋ Руна дня", callback_data="runes_daily"))
    builder.row(types.InlineKeyboardButton(text="ᛇ Руна ситуации", callback_data="runes_situation"))
    builder.row(types.InlineKeyboardButton(text="ᛖ Руна отношения", callback_data="runes_relationship"))
    
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("runes_"))
async def process_runes_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка всех callback-запросов рун"""
    data = callback.data
    
    # Определяем, это расклад или дополнительная опция
    spread_names = {
        "runes_one": "Одна руна",
        "runes_three": "Три руны",
        "runes_daily": "Руна дня",
        "runes_situation": "Руна ситуации",
        "runes_relationship": "Руна отношения"
    }
    
    if data in spread_names:
        # Это выбор расклада
        spread_name = spread_names[data]
        await state.update_data(spread_type=data, spread_name=spread_name)
        
        if data in ["runes_one", "runes_three", "runes_situation", "runes_relationship"]:
            await state.set_state(RunesDivination.waiting_for_question)
            text = f"""
Вы выбрали: *{spread_name}*

Теперь сформулируйте свой вопрос или опишите ситуацию.

*Примеры вопросов:*
• "Что ждёт меня в карьере?"
• "Как улучшить отношения с партнёром?"
• "Какой выбор будет правильным?"
• "Что нужно знать о текущей ситуации?"

Напишите ваш вопрос:
"""
            await callback.message.edit_text(text, parse_mode="Markdown")
        else:
            # Руна дня — сразу выдаём результат
            await generate_runes_reading(callback.message, state, "Какой совет на сегодня?")
            await state.clear()
        
        await callback.answer()
        
    elif data == "runes_another":
        # Другой расклад
        await callback.answer("Используйте команду /runes для нового расклада.")
        # Можно вызвать cmd_runes, но для простоты просто уведомляем
        await callback.message.answer("Выберите новый расклад рун:", parse_mode="Markdown")
        
    elif data == "runes_all":
        # Все руны
        text = "📖 *Все руны старшего футарка:*\n\n"
        for rune in RUNES:
            text += f"*{rune['name']}* — {rune['meaning']}\n"
        
        text += "\n*Использование:* Для гадания выберите расклад в меню /runes"
        await callback.message.answer(text, parse_mode="Markdown")
        await callback.answer()
        
    else:
        await callback.answer("Неизвестная опция рун.")


@router.message(RunesDivination.waiting_for_question)
async def process_runes_question(message: Message, state: FSMContext):
    """Обработка вопроса для рун"""
    question = message.text
    await generate_runes_reading(message, state, question)
    await state.clear()


async def generate_runes_reading(message: Message, state: FSMContext, question: str):
    """Генерация расклада рун"""
    data = await state.get_data()
    spread_type = data.get("spread_type", "runes_one")
    spread_name = data.get("spread_name", "Расклад рун")
    
    # Выбор случайных рун
    if spread_type == "runes_one":
        runes_count = 1
    elif spread_type == "runes_three":
        runes_count = 3
    else:
        runes_count = 1
    
    selected_runes = random.sample(RUNES, runes_count)
    
    # Определение положения (прямое или перевёрнутое) и сбор деталей
    positions = []
    rune_details = []
    for i, rune in enumerate(selected_runes):
        position = random.choice(["прямое", "перевёрнутое"])
        positions.append(position)
        rune_details.append({
            "rune_number": i + 1,
            "name": rune["name"],
            "meaning": rune["meaning"],
            "position": position
        })
    
    # Формирование текста расклада
    reading_text = f"""
ᚱ *{spread_name}*
*Вопрос:* {question}

"""
    
    if spread_type == "runes_three":
        reading_text += "*Три руны — Прошлое, Настоящее, Будущее:*\n\n"
        time_labels = ["Прошлое", "Настоящее", "Будущее"]
        for i, (rune, pos) in enumerate(zip(selected_runes, positions)):
            reading_text += f"*{time_labels[i]}:* {rune['name']} ({pos})\n"
            reading_text += f"*Значение:* {rune['meaning']}\n\n"
    else:
        rune = selected_runes[0]
        pos = positions[0]
        reading_text += f"*Выпала руна:* {rune['name']} ({pos})\n"
        reading_text += f"*Значение:* {rune['meaning']}\n\n"
    
    # Общая интерпретация
    reading_text += """
*Интерпретация:*
Руны советуют доверять своей интуиции и действовать в соответствии с внутренней правдой.

*Совет рун:*
Будьте внимательны к знакам судьбы и не игнорируйте свои истинные желания.

✨ *Помните:* Руны показывают потенциал ситуации, но окончательный выбор всегда за вами.
"""
    
    # Сохраняем в историю предсказаний
    try:
        async with get_session_maker()() as session:
            await PredictionHistoryService.create_prediction(
                session=session,
                user_id=message.from_user.id,
                prediction_type=PredictionType.RUNES,
                subtype=spread_type,
                details=rune_details,
                result_text=reading_text,
                user_message=question,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
            )
    except Exception as e:
        log.error(f"Ошибка при сохранении истории предсказаний рун: {e}")
        # Продолжаем выполнение, не прерывая работу бота
    
    await message.answer(reading_text, parse_mode="Markdown")
    
    # Дополнительные опции
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="ᚱ Другой расклад", callback_data="runes_another"))
    builder.row(types.InlineKeyboardButton(text="📖 Значение всех рун", callback_data="runes_all"))
    
    await message.answer("Что дальше?", reply_markup=builder.as_markup())


# Этот обработчик удалён, функциональность перенесена в process_runes_callback


# Обработка текстовых кнопок
@router.message(F.text.contains("руны"))
async def handle_runes_button(message: Message, state: FSMContext):
    """Обработка нажатия кнопки 'Руны'"""
    await cmd_runes(message, state)