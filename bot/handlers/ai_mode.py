"""
Обработчик режима ИИ: переключение режима, при котором все текстовые сообщения обрабатываются ИИ.
"""

import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.user_settings import UserSettingsService
from bot.services.llm import get_llm_service
from bot.services.history import ConsultationHistory
from bot.services.order import OrderService
from bot.services.hybrid_draft import HybridDraftService
from bot.database.engine import get_session_maker
from bot.config import Settings

router = Router()
log = logging.getLogger(__name__)
settings = Settings()


# Состояния для гибридного режима (оставлено для совместимости, но не используется)
class HybridModeStates(StatesGroup):
    waiting_for_edit = State()


@router.message(F.text == "🔘 Режим ИИ")
async def handle_ai_mode_button(message: Message, state: FSMContext):
    """Обработчик кнопки переключения режима ИИ."""
    user_id = message.from_user.id
    
    async with get_session_maker()() as session:
        # Получаем текущее состояние режима
        current = await UserSettingsService.get_ai_mode(session, user_id)
        new_state = not current
        
        # Обновляем настройки
        await UserSettingsService.set_ai_mode(session, user_id, new_state)
        
        # Сообщение пользователю
        if new_state:
            response = """
✅ *Режим ИИ включён*

Теперь все ваши текстовые сообщения (кроме кнопок меню) будут обрабатываться ИИ.

*Как это работает:*
1. Напишите любой вопрос или фразу
2. Бот отправит запрос к Perplexity AI
3. Вы получите развёрнутый ответ

*Чтобы выключить режим:* снова нажмите кнопку «🔘 Режим ИИ».
"""
        else:
            response = "✅ *Режим ИИ выключён* — возврат к обычному меню."
        
        await message.answer(response, parse_mode="Markdown")


@router.message(F.text == "🔄 Гибридный режим")
async def handle_hybrid_mode_button(message: Message, state: FSMContext):
    """Обработчик кнопки переключения гибридного режима."""
    user_id = message.from_user.id
    
    async with get_session_maker()() as session:
        # Получаем текущее состояние режима
        current = await UserSettingsService.get_hybrid_mode(session, user_id)
        new_state = not current
        
        # Обновляем настройки
        await UserSettingsService.set_hybrid_mode(session, user_id, new_state)
        
        # Если включаем гибридный режим, выключаем обычный AI режим
        if new_state:
            await UserSettingsService.set_ai_mode(session, user_id, False)
        
        # Сообщение пользователю
        if new_state:
            response = """
🔄 *Гибридный режим включён*

Теперь ИИ будет отвечать на ваши вопросы автоматически.

*Как это работает:*
1. Напишите любой вопрос или фразу
2. ИИ сразу отправит развёрнутый ответ
3. При необходимости с вами свяжется консультант для уточнений

*Чтобы выключить режим:* снова нажмите кнопку «🔄 Гибридный режим».
"""
        else:
            response = "✅ *Гибридный режим выключён*."
        
        await message.answer(response, parse_mode="Markdown")


@router.message(F.text)
async def handle_text_in_ai_mode(message: Message, state: FSMContext, session_maker=None):
    """Обработчик текстовых сообщений в режиме ИИ."""
    user_id = message.from_user.id
    
    if session_maker is None:
        # Fallback для обратной совместимости (не должно происходить)
        from bot.database.engine import get_session_maker
        from bot.config import Settings
        settings = Settings()
        from bot.database.engine import create_engine
        engine = create_engine(settings.DATABASE_URL)
        session_maker = get_session_maker(engine)
    
    async with session_maker() as session:
        # Проверяем, включен ли режим ИИ
        ai_mode = await UserSettingsService.get_ai_mode(session, user_id)
        hybrid_mode = await UserSettingsService.get_hybrid_mode(session, user_id)
        
        if not ai_mode and not hybrid_mode:
            # Режим не активен, пропускаем (другие обработчики справятся)
            return
        
        # Проверяем, что сообщение не начинается с команды
        if message.text.startswith('/'):
            return
        
        # Проверяем, что это не кнопка меню (обработано другими обработчиками)
        # Если мы здесь, значит, другие обработчики не перехватили сообщение
        
        question = message.text.strip()
        if not question:
            return
        
        log.info(f"AI mode request from {user_id}: {question[:100]}...")
        
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
        
        # Увеличиваем счётчик запросов ИИ
        await UserSettingsService.increment_ai_request_count(session, user_id)
        
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
        
        # Если гибридный режим, сохраняем черновик для возможной проверки консультантом
        if hybrid_mode:
            # Сохраняем черновик в базу для проверки человеком
            try:
                draft = await HybridDraftService.create_draft(
                    session=session,
                    user_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    question=question,
                    ai_draft=answer_text
                )
                
                # Уведомляем администратора о новом черновике
                admin_id = settings.ADMIN_USER_ID
                if admin_id:
                    try:
                        admin_notification = (
                            f"🔄 *Новый черновик для проверки*\n\n"
                            f"🆔 *Черновик #{draft.id}*\n"
                            f"👤 Пользователь: {message.from_user.first_name or 'Неизвестно'} (@{message.from_user.username or 'нет'})\n"
                            f"❓ Вопрос: {question[:200]}...\n\n"
                            f"Для просмотра используйте команду /admin_drafts"
                        )
                        await message.bot.send_message(
                            chat_id=admin_id,
                            text=admin_notification,
                            parse_mode="Markdown"
                        )
                        log.info(f"Администратор {admin_id} уведомлён о черновике #{draft.id}")
                    except Exception as e:
                        log.error(f"Ошибка при уведомлении администратора: {e}")
                
                log.info(f"Черновик #{draft.id} сохранён для проверки человеком")
            except Exception as e:
                log.error(f"Ошибка при сохранении черновика: {e}")
        
        # Если режим ИИ активен, предлагаем кнопку выхода
        if ai_mode:
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(
                text="❌ Выключить режим ИИ",
                callback_data="disable_ai_mode"
            ))
            await message.answer(
                "🔘 *Режим ИИ активен*\n\n"
                "Вы можете продолжать задавать вопросы.\n"
                "Чтобы выключить режим, нажмите кнопку ниже:",
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
        
        # Не очищаем состояние, чтобы можно было продолжать диалог


@router.callback_query(lambda c: c.data == "edit_draft")
async def handle_edit_draft(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки редактирования черновика."""
    await callback.answer()
    
    # Переходим в состояние ожидания редактирования
    await state.set_state(HybridModeStates.waiting_for_edit)
    
    await callback.message.answer(
        "✏️ *Редактирование черновика*\n\n"
        "Отправьте исправленный текст ответа. Вы можете полностью изменить текст или отредактировать частично.\n\n"
        "Когда закончите — просто отправьте сообщение.",
        parse_mode="Markdown"
    )


@router.callback_query(lambda c: c.data == "send_draft")
async def handle_send_draft(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки отправки черновика как есть."""
    await callback.answer()
    
    # Получаем данные черновика
    data = await state.get_data()
    draft_answer = data.get('draft_answer')
    draft_question = data.get('draft_question')
    
    if draft_answer:
        # Отправляем финальный ответ (уже отправлен ранее, просто подтверждаем)
        await callback.message.answer("✅ *Черновик отправлен как есть.*", parse_mode="Markdown")
    else:
        await callback.message.answer("⚠️ *Ошибка:* Черновик не найден.", parse_mode="Markdown")
    
    # Очищаем состояние
    await state.clear()


@router.message(HybridModeStates.waiting_for_edit)
async def handle_edited_draft(message: Message, state: FSMContext):
    """Обработчик отредактированного черновика."""
    user_id = message.from_user.id
    edited_text = message.text.strip()
    
    if not edited_text:
        await message.answer("❌ Текст не может быть пустым. Попробуйте снова.")
        return
    
    # Получаем оригинальный черновик
    data = await state.get_data()
    draft_question = data.get('draft_question', 'Неизвестный вопрос')
    original_answer = data.get('draft_answer')
    
    # Форматируем отредактированный ответ
    final_answer = f"""
🧠 *Вопрос:* {draft_question}

{edited_text}

✨ *Отредактировано пользователем.*
"""
    
    # Отправляем финальный ответ
    await message.answer(final_answer, parse_mode="Markdown")
    
    # Сохраняем отредактированную консультацию в историю
    async with get_session_maker()() as session:
        try:
            await ConsultationHistory.add(
                session=session,
                user_id=user_id,
                question=draft_question,
                answer=final_answer
            )
            log.debug(f"Отредактированная консультация сохранена для пользователя {user_id}")
            
            # Обновляем статистику пользователя
            await UserSettingsService.increment_consultation_count(session, user_id)
        except Exception as e:
            log.error(f"Ошибка при сохранении отредактированной консультации: {e}")
    
    # Очищаем состояние
    await state.clear()
    
    await message.answer("✅ *Ответ отправлен после редактирования.*", parse_mode="Markdown")


@router.callback_query(lambda c: c.data == "disable_ai_mode")
async def handle_disable_ai_mode(callback: CallbackQuery):
    """Обработчик кнопки выключения режима ИИ."""
    user_id = callback.from_user.id
    
    async with get_session_maker()() as session:
        # Выключаем режим ИИ
        await UserSettingsService.set_ai_mode(session, user_id, False)
        
        await callback.answer("✅ Режим ИИ выключен.")
        
        # Обновляем сообщение с кнопкой
        await callback.message.edit_text(
            "✅ *Режим ИИ выключён*\n\n"
            "Теперь текстовые сообщения будут обрабатываться обычным меню.",
            parse_mode="Markdown"
        )


@router.callback_query(lambda c: c.data == "order_premium_consultation")
async def handle_order_premium_consultation(callback: CallbackQuery):
    """Обработчик кнопки заказа премиум-консультации."""
    await callback.answer()
    
    await callback.message.answer(
        "💎 *Консультация с магом (777 ₽)*\n\n"
        "Для заказа консультации нажмите кнопку «💎 Консультация (777 ₽)» в главном меню.\n\n"
        "После оплаты вы получите доступ к:\n"
        "• ИИ-режиму (15 запросов в день)\n"
        "• Персональному ответу от мага\n"
        "• Поддержке в течение 24 часов",
        parse_mode="Markdown"
    )

# Обратная совместимость с start.py
cmd_ai_enter = handle_ai_mode_button
