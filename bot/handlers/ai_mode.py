"""
MysticBot — AI Mode Handler
ИИ-режим: пользователь входит → пишет вопросы → получает ответы от LLM.
Поддержка: контекст диалога, выход по команде/кнопке/таймаут.
"""

import asyncio
import logging
import time
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from bot.config import settings
from bot.services.llm import get_llm_service, LLMError, AllProvidersFailedError

logger = logging.getLogger(__name__)

router = Router(name="ai_mode")

# ============================================================
# FSM States
# ============================================================

class AIMode(StatesGroup):
    """Состояния ИИ-режима."""
    active = State()            # Пользователь в режиме ИИ-диалога


# ============================================================
# Константы
# ============================================================

MAX_CONTEXT_MESSAGES = 20       # Макс. сообщений в контексте диалога
MAX_CONTEXT_TOKENS_APPROX = 24000  # ~24K токенов (оставляем запас из 32K)
AI_SESSION_TIMEOUT = 600        # 10 мин без активности → авто-выход
MAX_MESSAGE_LENGTH = 4096       # Лимит Telegram на длину сообщения

SYSTEM_PROMPT = """Ты — MysticBot, мистический ИИ-помощник в Telegram.
Отвечай на русском языке. Будь полезным, точным и дружелюбным.
Используй эмодзи для оформления ответов.
Если вопрос касается эзотерики, Таро, астрологии — давай развёрнутые ответы.
Для остальных тем — отвечай как универсальный ассистент."""


# ============================================================
# Клавиатуры
# ============================================================

def get_ai_mode_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура во время ИИ-режима."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔮 Новый диалог"), KeyboardButton(text="❌ Выйти из ИИ")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напишите вопрос для ИИ...",
    )


def get_ai_enter_button() -> InlineKeyboardMarkup:
    """Инлайн-кнопка входа в ИИ-режим."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Войти в ИИ-режим", callback_data="ai_mode_enter")],
    ])


def get_ai_inline_controls() -> InlineKeyboardMarkup:
    """Инлайн-кнопки под ответом ИИ."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Переспросить", callback_data="ai_retry"),
            InlineKeyboardButton(text="🔮 Новый диалог", callback_data="ai_new_chat"),
            InlineKeyboardButton(text="❌ Выход", callback_data="ai_exit"),
        ],
    ])


# ============================================================
# Вспомогательные функции
# ============================================================

def _estimate_tokens(text: str) -> int:
    """Грубая оценка токенов (1 токен ≈ 3.5 символа для русского)."""
    return len(text) // 3


def _trim_context(
    messages: list[dict],
    max_messages: int = MAX_CONTEXT_MESSAGES,
    max_tokens: int = MAX_CONTEXT_TOKENS_APPROX,
) -> list[dict]:
    """
    Обрезка контекста диалога для вписывания в лимит.
    Системное сообщение всегда остаётся первым.
    """
    if not messages:
        return messages

    # Системное сообщение — всегда первое
    system_msg = messages[0] if messages[0]["role"] == "system" else None
    history = messages[1:] if system_msg else messages[:]

    # Ограничение по количеству
    if len(history) > max_messages:
        history = history[-max_messages:]

    # Ограничение по токенам (удаляем старые сообщения)
    total_tokens = sum(_estimate_tokens(m["content"]) for m in history)
    if system_msg:
        total_tokens += _estimate_tokens(system_msg["content"])

    while total_tokens > max_tokens and len(history) > 2:
        removed = history.pop(0)
        total_tokens -= _estimate_tokens(removed["content"])

    result = []
    if system_msg:
        result.append(system_msg)
    result.extend(history)
    return result


async def _get_ai_context(state: FSMContext) -> dict:
    """Получение данных ИИ-сессии из FSM."""
    data = await state.get_data()
    return {
        "messages": data.get("ai_messages", []),
        "last_activity": data.get("ai_last_activity", 0),
        "request_count": data.get("ai_request_count", 0),
        "session_start": data.get("ai_session_start", 0),
    }


async def _save_ai_context(
    state: FSMContext,
    messages: list[dict],
    request_count: int,
    session_start: float,
) -> None:
    """Сохранение данных ИИ-сессии в FSM."""
    await state.update_data(
        ai_messages=messages,
        ai_last_activity=time.time(),
        ai_request_count=request_count,
        ai_session_start=session_start,
    )


async def _send_long_message(message: Message, text: str, **kwargs) -> Message:
    """Отправка длинного сообщения с разбивкой по лимиту Telegram."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return await message.answer(text, **kwargs)

    # Разбиваем по абзацам
    parts = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 > MAX_MESSAGE_LENGTH:
            if current:
                parts.append(current.strip())
            current = paragraph
        else:
            current += "\n\n" + paragraph if current else paragraph

    if current:
        parts.append(current.strip())

    last_msg = None
    for i, part in enumerate(parts):
        # Кнопки только под последним сообщением
        if i == len(parts) - 1:
            last_msg = await message.answer(part, **kwargs)
        else:
            last_msg = await message.answer(part)
        await asyncio.sleep(0.3)  # Anti-flood

    return last_msg


# ============================================================
# Handlers: Вход в ИИ-режим
# ============================================================

@router.message(Command("ai"))
async def cmd_ai_enter(message: Message, state: FSMContext) -> None:
    """Команда /ai — вход в ИИ-режим."""
    if not settings.features.ai_mode_enabled:
        await message.answer("⚠️ ИИ-режим временно отключён администратором.")
        return

    providers = settings.llm_providers_order
    if not providers:
        await message.answer("❌ Ни один LLM-провайдер не настроен. Обратитесь к администратору.")
        return

    # Инициализация сессии
    now = time.time()
    initial_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    await state.set_state(AIMode.active)
    await _save_ai_context(
        state,
        messages=initial_messages,
        request_count=0,
        session_start=now,
    )

    provider_name = providers[0].capitalize()
    await message.answer(
        f"🤖 **ИИ-режим активирован!**\n\n"
        f"🔹 Провайдер: {provider_name}\n"
        f"🔹 Контекст: до {MAX_CONTEXT_MESSAGES} сообщений\n"
        f"🔹 Таймаут: {AI_SESSION_TIMEOUT // 60} мин без активности\n\n"
        f"Просто пишите вопросы — я отвечу!\n\n"
        f"_Для выхода: /exit, кнопка «❌ Выйти из ИИ» или 10 мин тишины_",
        reply_markup=get_ai_mode_keyboard(),
        parse_mode="Markdown",
    )
    logger.info(f"🤖 User {message.from_user.id} вошёл в ИИ-режим")


@router.callback_query(F.data == "ai_mode_enter")
async def cb_ai_enter(callback: CallbackQuery, state: FSMContext) -> None:
    """Инлайн-кнопка входа в ИИ-режим."""
    await callback.answer()
    # Переиспользуем логику команды /ai
    await cmd_ai_enter(callback.message, state)


# ============================================================
# Handlers: Выход из ИИ-режима
# ============================================================

@router.message(AIMode.active, Command("exit", "stop", "quit"))
async def cmd_ai_exit(message: Message, state: FSMContext) -> None:
    """Команды /exit, /stop, /quit — выход из ИИ-режима."""
    await _exit_ai_mode(message, state, reason="команда")


@router.message(AIMode.active, F.text == "❌ Выйти из ИИ")
async def btn_ai_exit(message: Message, state: FSMContext) -> None:
    """Кнопка «Выйти из ИИ» — выход."""
    await _exit_ai_mode(message, state, reason="кнопка")


@router.callback_query(F.data == "ai_exit")
async def cb_ai_exit(callback: CallbackQuery, state: FSMContext) -> None:
    """Инлайн-кнопка выхода."""
    await callback.answer("ИИ-режим завершён")
    await _exit_ai_mode(callback.message, state, reason="инлайн-кнопка")


async def _exit_ai_mode(message: Message, state: FSMContext, reason: str = "") -> None:
    """Общая логика выхода из ИИ-режима."""
    ctx = await _get_ai_context(state)
    duration = time.time() - ctx["session_start"] if ctx["session_start"] else 0

    await state.clear()

    await message.answer(
        f"👋 **ИИ-режим завершён**\n\n"
        f"📊 Запросов за сессию: {ctx['request_count']}\n"
        f"⏱️ Длительность: {int(duration // 60)} мин {int(duration % 60)} сек\n"
        f"📝 Причина выхода: {reason}",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown",
    )
    logger.info(
        f"👋 User {message.chat.id} вышел из ИИ-режима "
        f"({reason}, {ctx['request_count']} запросов, {int(duration)}с)"
    )


# ============================================================
# Handlers: Управление диалогом
# ============================================================

@router.message(AIMode.active, F.text == "🔮 Новый диалог")
async def btn_new_chat(message: Message, state: FSMContext) -> None:
    """Кнопка «Новый диалог» — очистка контекста."""
    ctx = await _get_ai_context(state)
    initial_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    await _save_ai_context(
        state,
        messages=initial_messages,
        request_count=ctx["request_count"],
        session_start=ctx["session_start"],
    )

    await message.answer(
        "🔮 **Контекст очищен!** Начинаем новый диалог.\n"
        "Задайте вопрос:",
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "ai_new_chat")
async def cb_new_chat(callback: CallbackQuery, state: FSMContext) -> None:
    """Инлайн-кнопка «Новый диалог»."""
    await callback.answer("Контекст очищен")
    await btn_new_chat(callback.message, state)


@router.callback_query(F.data == "ai_retry")
async def cb_retry(callback: CallbackQuery, state: FSMContext) -> None:
    """Инлайн-кнопка «Переспросить» — повтор последнего запроса."""
    await callback.answer("Переспрашиваю...")

    ctx = await _get_ai_context(state)
    messages = ctx["messages"]

    if len(messages) < 2:
        await callback.message.answer("❌ Нет предыдущего запроса для повтора.")
        return

    # Удаляем последний ответ ИИ (если есть) и повторяем запрос
    if messages[-1]["role"] == "assistant":
        messages = messages[:-1]

    await _process_ai_request(callback.message, state, messages, ctx["request_count"])


# ============================================================
# Handlers: Обработка текстовых сообщений в ИИ-режиме
# ============================================================

@router.message(AIMode.active, F.text)
async def handle_ai_message(message: Message, state: FSMContext) -> None:
    """
    Главный обработчик — текст пользователя в ИИ-режиме.
    Отправляет запрос к LLM с контекстом диалога.
    """
    ctx = await _get_ai_context(state)

    # Проверка таймаута сессии
    if ctx["last_activity"] and (time.time() - ctx["last_activity"]) > AI_SESSION_TIMEOUT:
        await _exit_ai_mode(message, state, reason="таймаут (10 мин)")
        return

    # Проверка дневного лимита
    if ctx["request_count"] >= settings.features.daily_ai_limit:
        await message.answer(
            f"⚠️ Достигнут дневной лимит: {settings.features.daily_ai_limit} запросов.\n"
            f"Попробуйте завтра или обратитесь к администратору.",
        )
        return

    # Формируем контекст
    messages = ctx["messages"]
    messages.append({"role": "user", "content": message.text})
    messages = _trim_context(messages)

    await _process_ai_request(message, state, messages, ctx["request_count"])


async def _process_ai_request(
    message: Message,
    state: FSMContext,
    messages: list[dict],
    request_count: int,
) -> None:
    """Отправка запроса к LLM и обработка ответа."""
    # Индикатор «печатает...»
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    llm = get_llm_service()

    try:
        data = await llm.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=4096,
        )

        # Извлекаем ответ
        ai_text = data["choices"][0]["message"]["content"]

        # Сохраняем в контекст
        messages.append({"role": "assistant", "content": ai_text})
        ctx = await _get_ai_context(state)
        await _save_ai_context(
            state,
            messages=messages,
            request_count=request_count + 1,
            session_start=ctx["session_start"],
        )

        # Отправляем с инлайн-кнопками
        await _send_long_message(
            message,
            ai_text,
            reply_markup=get_ai_inline_controls(),
            parse_mode="Markdown",
        )

    except AllProvidersFailedError as e:
        logger.error(f"❌ Все провайдеры недоступны: {e}")
        await message.answer(
            "❌ Все ИИ-провайдеры временно недоступны.\n"
            "Попробуйте через минуту или напишите /exit для выхода.",
        )

    except LLMError as e:
        logger.error(f"❌ LLM ошибка: {e}")
        await message.answer(
            f"⚠️ Ошибка ИИ: {str(e)[:200]}\n"
            f"Попробуйте переформулировать вопрос.",
        )

    except Exception as e:
        logger.exception(f"💥 Неожиданная ошибка в ИИ-режиме: {e}")
        await message.answer(
            "💥 Произошла непредвиденная ошибка. Попробуйте ещё раз.",
        )


async def handle_ai_mode_button(message: Message, state: FSMContext):
    """Обработчик кнопки входа в ИИ-режим"""
    await message.answer(
        "🔘 Вы вошли в ИИ-режим. Теперь все ваши текстовые сообщения будут обрабатываться ИИ.\n"
        "Для выхода нажмите кнопку ❌ Выйти из ИИ или отправьте /exit.",
        reply_markup=get_ai_mode_keyboard(),
    )
    await state.set_state(AIMode.active)


async def handle_hybrid_mode_button(message: Message, state: FSMContext):
    """Обработчик кнопки гибридного режима"""
    await message.answer(
        "🔄 Гибридный режим активирован.\n"
        "Вы можете отправить вопрос, получите черновик ответа, который можно редактировать.",
        reply_markup=get_ai_mode_keyboard(),
    )
    await state.set_state(AIMode.active)
