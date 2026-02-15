"""
Обработчики для консультаций с Perplexity AI
"""

import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.llm import get_llm_service
from bot.services.history import ConsultationHistory
from bot.services.user_settings import UserSettingsService
from bot.services.order import OrderService
from bot.database.engine import get_session_maker
from bot.config import Settings

router = Router()
log = logging.getLogger(__name__)
settings = Settings()


# Состояния для консультации
class Consultation(StatesGroup):
    waiting_for_question = State()  # Ожидание вопроса


@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    """Команда /ask - консультация с AI"""
    if not settings.is_llm_configured:
        await message.answer(
            "⚠️ *Сервис консультаций временно недоступен*\n\n"
            "Для работы этой функции нужен API-ключ Perplexity AI или OpenAI.\n"
            "Если вы администратор, добавьте ключ в файл .env",
            parse_mode="Markdown"
        )
        return
    
    user_id = message.from_user.id
    
    async with get_session_maker()() as session:
        # Проверяем, является ли пользователь платным подписчиком
        order_service = OrderService(session)
        is_premium = await order_service.has_paid_order(user_id)
        
        # Проверяем лимиты запросов
        can_request, reason = await UserSettingsService.can_make_ai_request(
            session, user_id, is_premium
        )
        
        if not can_request:
            await message.answer(reason, parse_mode="Markdown")
            
            # Если пользователь не платный, предлагаем заказать консультацию
            if not is_premium:
                builder = InlineKeyboardBuilder()
                builder.row(types.InlineKeyboardButton(
                    text="💎 Заказать консультацию",
                    callback_data="order_premium_consultation"
                ))
                await message.answer(
                    "💎 Получите доступ к ИИ-консультациям\n\n"
                    "Закажите персональную консультацию за 777 ₽ и получите:\n"
                    "• Доступ к ИИ-режиму (15 запросов в день)\n"
                    "• Персональный ответ от мага\n"
                    "• Поддержку в течение 24 часов",
                    reply_markup=builder.as_markup(),
                    parse_mode="Markdown"
                )
            return
    
    await state.set_state(Consultation.waiting_for_question)
    
    text = """
🤖 *Консультация с AI-экспертом*

Задайте любой вопрос в области:
• Карт Таро и эзотерики
• Нумерологии и астрологии
• Психологии и саморазвития
• Отношений и карьеры
• Духовных практик

*Примеры вопросов:*
• "Как понять, что мне делать в сложной ситуации?"
• "Как развивать интуицию?"
• "Что такое кармические отношения?"
• "Как выбрать правильный путь в жизни?"

Напишите ваш вопрос:
"""
    
    await message.answer(text, parse_mode="Markdown")


@router.message(Consultation.waiting_for_question)
async def process_ai_question(message: Message, state: FSMContext, session_maker=None):
    """Обработка вопроса для AI"""
    question = message.text.strip()
    user_id = message.from_user.id
    
    log.info(f"AI consultation request from {user_id}: {question[:100]}...")
    
    # Создаём сессию, если не передана
    local_session = None
    if not session_maker:
        session_maker = get_session_maker()
    
    # Проверяем лимиты и платный статус перед генерацией
    async with session_maker() as session:
        order_service = OrderService(session)
        is_premium = await order_service.has_paid_order(user_id)
        can_request, reason = await UserSettingsService.can_make_ai_request(
            session, user_id, is_premium
        )
        
        if not can_request:
            await message.answer(reason, parse_mode="Markdown")
            await state.clear()
            return
        
        # Увеличиваем счётчик запросов ИИ
        await UserSettingsService.increment_ai_request_count(session, user_id)
        
        # Показываем статус "думаю"
        thinking_msg = await message.answer("🤔 *AI думает...*", parse_mode="Markdown")
        
        # Получаем сервис LLM
        llm_service = get_llm_service(settings)
        
        # Генерируем ответ
        response = await llm_service.generate_interpretation(
            prompt=question,
            context="Пользователь просит консультацию по эзотерическому вопросу."
        )
        
        # Удаляем сообщение "думаю"
        await thinking_msg.delete()
        
        answer_text = None
        if response:
            # Форматируем ответ
            answer_text = f"""
🧠 *Вопрос:* {question}

{response}

✨ *Совет от MysticBot:* Используйте эту информацию как руководство, но всегда доверяйте своей интуиции.
"""
            await message.answer(answer_text, parse_mode="Markdown")
        else:
            # Если AI не ответил, проверяем причину
            if not settings.is_llm_configured:
                # Нет настроенного API ключа
                error_text = f"""
🧠 *Вопрос:* {question}

⚠️ *ИИ-режим временно недоступен*

Для работы ИИ-режима необходимо настроить API-ключ Perplexity или OpenAI.

*Что делать:*
1. Получите API-ключ на [platform.perplexity.ai](https://platform.perplexity.ai)
2. Добавьте его в файл `.env` как `PERPLEXITY_API_KEY=ваш_ключ`
3. Перезапустите бота

Или используйте альтернативный ключ OpenAI:
1. Получите ключ на [platform.openai.com](https://platform.openai.com)
2. Добавьте в `.env` как `OPENAI_API_KEY=sk-...`
3. Перезапустите бота

*Технические детали:* Отсутствует настроенный ключ LLM.
"""
            else:
                # API ключ есть, но API не ответил
                error_text = f"""
🧠 *Вопрос:* {question}

⚠️ *ИИ-режим временно недоступен*

Perplexity API не ответил на запрос. Возможные причины:
- Недействительный или просроченный API-ключ
- Закончились кредиты на счету
- Проблемы с сетью или доступом к API
- Ошибка на стороне сервиса Perplexity

*Что делать:*
1. Проверьте ключ на [platform.perplexity.ai](https://platform.perplexity.ai)
2. Убедитесь, что есть доступные кредиты
3. Попробуйте использовать OpenAI API (добавьте `OPENAI_API_KEY` в `.env`)
4. Перезапустите бота

*Технические детали:* Perplexity API вернул ошибку или timeout.
"""
            answer_text = error_text
            await message.answer(answer_text, parse_mode="Markdown")
        
        # Сохраняем консультацию в историю
        if answer_text:
            try:
                await ConsultationHistory.add(
                    session=session,
                    user_id=user_id,
                    question=question,
                    answer=answer_text
                )
                log.debug(f"Консультация сохранена для пользователя {user_id}")
                
                # Обновляем статистику пользователя
                await UserSettingsService.increment_consultation_count(session, user_id)
            except Exception as e:
                log.error(f"Ошибка при сохранении консультации: {e}")
                # Не прерываем выполнение из-за ошибки БД
    
    await state.clear()
    
    # Предложить ещё вопросы
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔄 Новый вопрос", callback_data="ask_new"))
    builder.row(types.InlineKeyboardButton(text="📚 Темы для консультации", callback_data="ask_topics"))
    
    await message.answer("Есть ещё вопросы?", reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data.startswith("ask_"))
async def process_ask_extras(callback: CallbackQuery):
    """Обработка дополнительных опций консультации"""
    option = callback.data
    
    if option == "ask_new":
        text = "Задайте новый вопрос для консультации с AI:"
        await callback.message.answer(text, parse_mode="Markdown")
    elif option == "ask_topics":
        text = """
📚 *Темы для консультаций:*

*Эзотерика и духовность:*
• Карты Таро и их значения
• Рунические расклады
• Нумерология и числа судьбы
• Астрологические прогнозы
• Медитация и энергетические практики

*Психология и отношения:*
• Понимание себя и своих желаний
• Отношения с партнёром, семьёй, коллегами
• Принятие сложных решений
• Преодоление страхов и тревог
• Поиск жизненного предназначения

*Практические вопросы:*
• Карьера и профессиональный рост
• Финансовые решения
• Здоровье и благополучие
• Творчество и самореализация
• Личностный рост и развитие

Задайте вопрос по любой из этих тем!
"""
        await callback.message.answer(text, parse_mode="Markdown")
    
    await callback.answer()


# Обработка текстовых кнопок (если добавим кнопку "Консультация AI")
@router.message(F.text.contains("консультация"))
async def handle_ask_button(message: Message, state: FSMContext):
    """Обработка нажатия кнопки 'Консультация AI'"""
    await cmd_ask(message, state)