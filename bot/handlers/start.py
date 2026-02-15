"""
Обработчики команд /start и главного меню
"""

import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import ReplyKeyboardBuilder


router = Router()


def build_main_keyboard() -> types.ReplyKeyboardMarkup:
    """Создает главную клавиатуру меню."""
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🃏 Карты Таро"))
    builder.row(types.KeyboardButton(text="🔢 Нумерология"))
    builder.row(types.KeyboardButton(text="♈️ Гороскоп"))
    builder.row(types.KeyboardButton(text="🌌 Астрология"))
    builder.row(types.KeyboardButton(text="🧘 Медитация"))
    builder.row(types.KeyboardButton(text="💰 Финансовый календарь"))
    builder.row(types.KeyboardButton(text="🎲 Случайное предсказание"))
    builder.row(types.KeyboardButton(text="📖 Сонник"), types.KeyboardButton(text="ᚱ Руны"))
    builder.row(types.KeyboardButton(text="🔘 Режим ИИ"))
    builder.row(types.KeyboardButton(text="🔄 Гибридный режим"))
    builder.row(types.KeyboardButton(text="💎 Консультация (777 ₽)"))
    builder.row(types.KeyboardButton(text="👤 Профиль"))
    return builder.as_markup(resize_keyboard=True)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""
    logging.info(f"Received /start from {message.from_user.id}")
    user = message.from_user

    welcome_text = f"""
✨ Добро пожаловать, {user.first_name}!

Я — MysticBot, ваш персональный эзотерический помощник.

🃏 *Карты Таро* — получайте мудрые советы и предсказания
🔢 *Нумерология* — раскройте тайны чисел вашей судьбы
♈️ *Гороскопы* — ежедневные, недельные и месячные прогнозы
💰 *Финансовый календарь* — астрологические рекомендации для финансов
👐 *Хиромантия* — анализ линий вашей ладони (скоро)
📖 *Сонник* — толкование снов
ᚱ *Руны* — древнее гадание

Выберите интересующую вас тему из меню ниже!
"""

    keyboard = build_main_keyboard()

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Обработчик команды /help — показывает краткую инструкцию и меню"""
    help_text = """
📖 *Помощь по MysticBot*

Я работаю через кнопки меню — просто выберите нужный раздел ниже!

*Основные разделы:*
🃏 Карты Таро — расклады и предсказания
🔢 Нумерология — числа судьбы
♈️ Гороскоп — прогнозы по знакам зодиака
🌌 Астрология — натальная карта, транзиты, совместимость
🧘 Медитация — практики для ума и тела
💰 Финансовый календарь — астрологические рекомендации
📖 Сонник — толкование снов
ᚱ Руны — древнее гадание
🎲 Случайное предсказание — мгновенная мудрость
🔘 Режим ИИ — все текстовые сообщения обрабатываются ИИ
🔄 Гибридный режим — черновик ответа с возможностью редактирования
💎 Консультация (777 ₽) — персональная работа с магом
👤 Профиль — ваши настройки и статистика

*Как пользоваться:*
1. Нажмите на кнопку нужного раздела
2. Следуйте подсказкам бота
3. Получайте персонализированные результаты

Всё просто — никаких команд запоминать не нужно! ✨
"""
    # Показываем то же меню, что и в /start
    keyboard = build_main_keyboard()

    await message.answer(help_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(Command("premium"))
async def cmd_premium(message: Message) -> None:
    """Информация о премиум-подписке"""
    premium_text = """
🌟 Премиум-подписка MysticBot

Что входит:
✅ Неограниченные расклады Таро
✅ Расширенные нумерологические отчёты
✅ Подробные гороскопы на месяц
✅ Персональный финансовый календарь
✅ Приоритетная поддержка
✅ Новые функции первыми

Стоимость: 299 ₽/месяц

Для оформления подписки свяжитесь с @admin
"""
    await message.answer(premium_text, parse_mode="Markdown")


@router.message(Command("price"))
async def cmd_price(message: Message) -> None:
    """Информация о персональной консультации"""
    logging.info(f"Received /price from {message.from_user.id}")
    price_text = """
💎 Персональная консультация мага

Что входит:
✅ Глубокий анализ вашей ситуации
✅ Подбор расклада Таро (5+ карт)
✅ Нумерологический портрет
✅ Астрологическая карта на месяц
✅ Персональные рекомендации
✅ Ответы на 3 ваших вопроса

Стоимость: 777 ₽ (единоразово)

Как заказать:
1. Нажмите кнопку «Заказать консультацию» ниже
2. Укажите ваш вопрос и дату рождения
3. Оплатите 777 ₽ на карту 2200 1234 5678 9012 (Тинькофф)
4. После оплаты отправьте скриншот чека @Mystictestadminbot для ручной проверки
5. Получите консультацию в течение 24 часов после подтверждения оплаты
"""
    # Создаем inline-клавиатуру с кнопкой заказа
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Заказать консультацию", callback_data="order_consultation")
    keyboard = builder.as_markup()

    await message.answer(price_text, reply_markup=keyboard, parse_mode=None)


@router.message(F.text.contains("💎 Консультация (777 ₽)"))
async def handle_price_button(message: Message) -> None:
    """Обработчик кнопки консультации"""
    await cmd_price(message)


# Обработчик перенесен в orders.py

# Обработчики текстовых кнопок главного меню
@router.message(F.text.contains("🃏 Карты Таро"))
async def handle_tarot_button(message: Message, state: FSMContext):
    """Обработчик кнопки Таро"""
    from bot.handlers.tarot import cmd_tarot
    await cmd_tarot(message, state)


@router.message(F.text.contains("🔢 Нумерология"))
async def handle_numerology_button(message: Message, state: FSMContext):
    """Обработчик кнопки нумерологии"""
    from bot.handlers.numerology import cmd_numerology
    await cmd_numerology(message, state)


@router.message(F.text.contains("♈️ Гороскоп"))
async def handle_horoscope_button(message: Message, state: FSMContext):
    """Обработчик кнопки гороскопа"""
    from bot.handlers.horoscope import cmd_horoscope
    await cmd_horoscope(message)


@router.message(F.text.contains("💰 Финансовый календарь"))
async def handle_finance_button(message: Message, state: FSMContext):
    """Обработчик кнопки финансового календаря"""
    from bot.handlers.finance_calendar import cmd_finance
    await cmd_finance(message)


@router.message(F.text.contains("🌌 Астрология"))
async def handle_astrology_button(message: Message, state: FSMContext):
    """Обработчик кнопки астрологии"""
    from bot.handlers.astrology import cmd_astrology
    await cmd_astrology(message, state)


@router.message(F.text.contains("🧘 Медитация"))
async def handle_meditation_button(message: Message, state: FSMContext):
    """Обработчик кнопки медитации"""
    from bot.handlers.meditation import cmd_meditation
    await cmd_meditation(message, state)


@router.message(F.text.contains("📖 Сонник"))
async def handle_dream_button(message: Message, state: FSMContext):
    """Обработчик кнопки сонника"""
    from bot.handlers.dream import cmd_dream
    await cmd_dream(message, state)


@router.message(F.text.contains("ᚱ Руны"))
async def handle_runes_button(message: Message, state: FSMContext):
    """Обработчик кнопки рун"""
    from bot.handlers.runes import cmd_runes
    await cmd_runes(message, state)


@router.message(F.text.contains("🎲 Случайное предсказание"))
async def handle_random_button(message: Message, state: FSMContext):
    """Обработчик кнопки случайного предсказания"""
    from bot.handlers.randomizer import cmd_random
    await cmd_random(message)


@router.message(F.text.contains("🤖 Консультация AI"))
async def handle_ask_button(message: Message, state: FSMContext):
    """Обработчик кнопки консультации AI"""
    from bot.handlers.ask import cmd_ask
    await cmd_ask(message, state)


@router.message(F.text.contains("👤 Профиль"))
async def handle_profile_button(message: Message):
    """Обработчик кнопки профиля"""
    from bot.handlers.profile import cmd_profile
    await cmd_profile(message)


@router.message(F.text.contains("🔘 Режим ИИ"))
async def handle_ai_mode_button(message: Message, state: FSMContext):
    """Обработчик кнопки режима ИИ"""
    from bot.handlers.ai_mode import handle_ai_mode_button as ai_mode_handler
    await ai_mode_handler(message, state)


@router.message(F.text.contains("🔄 Гибридный режим"))
async def handle_hybrid_mode_button(message: Message, state: FSMContext):
    """Обработчик кнопки гибридного режима"""
    from bot.handlers.ai_mode import handle_hybrid_mode_button
    await handle_hybrid_mode_button(message, state)
