"""
Административные команды
"""

import logging

from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.order import OrderService, OrderStatus
from bot.services.hybrid_draft import HybridDraftService
from bot.database.engine import get_session_maker
from bot.config import Settings

log = logging.getLogger(__name__)

router = Router()
settings = Settings()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return user_id == settings.ADMIN_USER_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Меню администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У вас нет прав администратора.")
        return
    
    admin_text = """
⚙️ *Панель администратора*

*Команды:*
/admin_stats — статистика бота
/admin_broadcast — рассылка сообщений
/admin_users — управление пользователями
/admin_db — управление базой данных
/admin_orders — управление заказами

*Быстрые действия:*
- Проверить состояние БД
- Посмотреть логи
- Добавить контент
"""
    await message.answer(admin_text, parse_mode="Markdown")


@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    """Статистика для администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён.")
        return
    
    stats_text = """
📈 *Административная статистика*

*Пользователи:*
- Всего: 1
- Новые за день: 1
- Активные за неделю: 1

*Запросы:*
- Всего: 0
- Успешных: 0
- Ошибок: 0

*Система:*
- Время работы: 0 ч 0 мин
- Использование памяти: ~50 MB
- База данных: работает
"""
    await message.answer(stats_text, parse_mode="Markdown")


@router.message(Command("admin_broadcast"))
async def cmd_admin_broadcast(message: Message, command: CommandObject, state: FSMContext):
    """Начать рассылку"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён.")
        return
    
    if not command.args:
        await message.answer("📢 *Рассылка*\n\nИспользование: `/admin_broadcast текст`", parse_mode="Markdown")
        return
    
    # Заглушка: просто эхо
    await message.answer(f"📢 Рассылка (заглушка):\n\n{command.args}")


@router.message(Command("admin_orders"))
async def cmd_admin_orders(message: Message):
    """Управление заказами"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён.")
        return
    
    async with get_session_maker()() as session:
        order_service = OrderService(session)
        
        # Получаем неоплаченные заказы
        unpaid_orders = await order_service.get_unpaid_orders(limit=20)
        
        if not unpaid_orders:
            await message.answer("✅ *Нет неоплаченных заказов.*", parse_mode="Markdown")
            return
        
        # Показываем список заказов
        response = "📋 *Неоплаченные заказы:*\n\n"
        for order in unpaid_orders:
            response += f"🆔 *Заказ #{order.id}*\n"
            response += f"👤 Пользователь: {order.first_name or 'Неизвестно'} (@{order.username or 'нет'})\n"
            response += f"📅 Дата рождения: {order.birth_date}\n"
            response += f"❓ Вопрос: {order.question[:100]}...\n"
            response += f"🕒 Создан: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            response += f"💳 Оплачен: {'✅' if order.is_paid else '❌'}\n"
            response += f"📸 Скриншот: {'Есть' if order.payment_screenshot else 'Нет'}\n"
            response += "—" * 30 + "\n"
        
        await message.answer(response, parse_mode="Markdown")
        
        # Для каждого заказа создаем inline-кнопки
        for order in unpaid_orders:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"confirm_payment:{order.id}"),
                types.InlineKeyboardButton(text="📝 Заметка", callback_data=f"add_note:{order.id}")
            )
            # Вторая строка: подробности и скриншот (если есть)
            buttons_row2 = []
            buttons_row2.append(types.InlineKeyboardButton(text="👀 Подробнее", callback_data=f"order_details:{order.id}"))
            if order.payment_screenshot:
                buttons_row2.append(types.InlineKeyboardButton(text="👁️ Раск.скриншот", callback_data=f"ocr_screenshot:{order.id}"))
            builder.row(*buttons_row2)
            
            order_text = (
                f"🆔 *Заказ #{order.id}*\n"
                f"👤 Пользователь: {order.first_name or 'Неизвестно'} (@{order.username or 'нет'})\n"
                f"❓ Вопрос: {order.question[:200]}..."
            )
            await message.answer(order_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("confirm_payment:"))
async def handle_confirm_payment(callback: CallbackQuery):
    """Обработчик подтверждения оплаты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        order_service = OrderService(session)
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден.", show_alert=True)
            return
        
        # Помечаем как оплаченный
        updated_order = await order_service.mark_as_paid(order_id)
        
        if updated_order and updated_order.is_paid:
            await callback.answer("✅ Заказ помечен как оплаченный.")
            
            # Обновляем сообщение
            await callback.message.edit_text(
                f"✅ *Заказ #{order_id} оплачен*\n\n"
                f"Пользователь: {order.first_name or 'Неизвестно'} (@{order.username or 'нет'})\n"
                f"Вопрос: {order.question[:200]}...\n\n"
                f"Статус: ОПЛАЧЕНО",
                parse_mode="Markdown"
            )
        else:
            await callback.answer("❌ Не удалось обновить заказ.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("add_note:"))
async def handle_add_note(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления заметки к заказу"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    # Сохраняем order_id в состоянии и просим прислать текст заметки
    await state.update_data(admin_note_order_id=order_id)
    await callback.answer()
    
    await callback.message.answer(
        f"📝 *Добавление заметки к заказу #{order_id}*\n\n"
        "Отправьте текст заметки. Она будет сохранена в информации о заказе.",
        parse_mode="Markdown"
    )


@router.message(F.text & F.from_user.id == settings.ADMIN_USER_ID)
async def handle_admin_note(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений администратора для добавления заметки"""
    data = await state.get_data()
    order_id = data.get("admin_note_order_id")
    
    if order_id:
        note_text = message.text.strip()
        if note_text:
            async with get_session_maker()() as session:
                order_service = OrderService(session)
                await order_service.add_admin_notes(order_id, note_text)
                
            await message.answer(f"✅ Заметка добавлена к заказу #{order_id}.")
            await state.clear()
        else:
            await message.answer("❌ Текст заметки не может быть пустым.")


@router.callback_query(lambda c: c.data.startswith("order_details:"))
async def handle_order_details(callback: CallbackQuery):
    """Обработчик просмотра деталей заказа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        order_service = OrderService(session)
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден.", show_alert=True)
            return
        
        details = (
            f"📋 *Детали заказа #{order.id}*\n\n"
            f"👤 *Пользователь:*\n"
            f"• ID: {order.user_id}\n"
            f"• Имя: {order.first_name or 'Неизвестно'}\n"
            f"• Username: @{order.username or 'нет'}\n\n"
            f"📅 *Дата рождения:* {order.birth_date}\n\n"
            f"❓ *Вопрос:*\n{order.question}\n\n"
            f"📊 *Статус:* {order.status.value}\n"
            f"💳 *Оплачен:* {'✅ Да' if order.is_paid else '❌ Нет'}\n"
            f"📸 *Скриншот:* {'Есть' if order.payment_screenshot else 'Нет'}\n\n"
            f"📝 *Заметки администратора:*\n{order.admin_notes or 'Нет'}\n\n"
            f"🕒 *Создан:* {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"✏️ *Обновлён:* {order.updated_at.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await callback.answer()
        await callback.message.answer(details, parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("ocr_screenshot:"))
async def handle_ocr_screenshot(callback: CallbackQuery):
    """Распознавание текста на скриншоте оплаты"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        order_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        order_service = OrderService(session)
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Заказ не найден.", show_alert=True)
            return
        
        if not order.payment_screenshot:
            await callback.answer("❌ У этого заказа нет скриншота.", show_alert=True)
            return
        
        # Информируем о начале обработки
        await callback.answer("🔍 Начинаю распознавание текста...")
        
        try:
            # Пытаемся импортировать EasyOCR
            import easyocr
            import tempfile
            import os
            from io import BytesIO
            
            # Скачиваем файл из Telegram
            # payment_screenshot может быть file_id
            file_id = order.payment_screenshot
            # Получаем объект файла
            file = await callback.bot.get_file(file_id)
            # Скачиваем файл во временный файл
            file_bytes = await callback.bot.download_file(file.file_path)
            
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp.write(file_bytes.read())
                tmp_path = tmp.name
            
            try:
                # Инициализируем читатель (русский + английский)
                reader = easyocr.Reader(['en', 'ru'], gpu=False)
                # Распознаём текст
                results = reader.readtext(tmp_path, detail=0, paragraph=True)
                
                # Формируем результат
                if results:
                    extracted_text = "\n".join(results)
                    # Ищем ключевые слова
                    keywords = ['перевод', 'оплата', 'чек', 'платеж', 'сумма', 'руб', '₽', '777']
                    found_keywords = [kw for kw in keywords if kw.lower() in extracted_text.lower()]
                    
                    result_message = (
                        f"👁️ *Распознанный текст с скриншота заказа #{order.id}*\n\n"
                        f"📄 *Извлечённый текст:*\n```\n{extracted_text[:1500]}"
                    )
                    if len(extracted_text) > 1500:
                        result_message += "\n... (текст обрезан)"
                    result_message += "\n```\n\n"
                    
                    if found_keywords:
                        result_message += f"✅ *Найдены ключевые слова:* {', '.join(found_keywords)}\n"
                    else:
                        result_message += "⚠️ *Ключевые слова не найдены*\n"
                    
                    result_message += f"\n*Совет:* Проверьте наличие суммы 777 ₽ и реквизитов."
                else:
                    result_message = f"❌ *Не удалось распознать текст на скриншоте заказа #{order.id}*"
                
                await callback.message.answer(result_message, parse_mode="Markdown")
                
            except Exception as e:
                await callback.message.answer(
                    f"❌ *Ошибка при распознавании текста:*\n```{str(e)[:500]}```",
                    parse_mode="Markdown"
                )
            finally:
                # Удаляем временный файл
                os.unlink(tmp_path)
                
        except ImportError:
            # EasyOCR не установлен
            await callback.message.answer(
                f"📸 *Скриншот заказа #{order.id}*\n\n"
                f"Функция OCR недоступна. Установите EasyOCR:\n"
                f"```pip install easyocr```\n\n"
                f"File ID: `{order.payment_screenshot}`\n"
                f"Вручную проверьте скриншот на наличие оплаты 777 ₽.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await callback.message.answer(
                f"❌ *Ошибка при обработке скриншота:*\n```{str(e)[:500]}```",
                parse_mode="Markdown"
            )


@router.message(Command("admin_drafts"))
async def cmd_admin_drafts(message: Message):
    """Просмотр черновиков, ожидающих проверки человеком"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Доступ запрещён.")
        return
    
    async with get_session_maker()() as session:
        # Получаем черновики, ожидающие проверки
        pending_drafts = await HybridDraftService.get_pending_drafts(session, limit=20)
        
        if not pending_drafts:
            await message.answer("✅ *Нет черновиков, ожидающих проверки.*", parse_mode="Markdown")
            return
        
        # Показываем список черновиков
        response = "📋 *Черновики на проверку:*\n\n"
        for draft in pending_drafts:
            response += f"🆔 *Черновик #{draft.id}*\n"
            response += f"👤 Пользователь: {draft.first_name or 'Неизвестно'} (@{draft.username or 'нет'})\n"
            response += f"❓ Вопрос: {draft.question[:100]}...\n"
            response += f"🕒 Создан: {draft.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            response += "—" * 30 + "\n"
        
        await message.answer(response, parse_mode="Markdown")
        
        # Для каждого черновика создаем inline-кнопки
        for draft in pending_drafts:
            builder = InlineKeyboardBuilder()
            builder.row(
                types.InlineKeyboardButton(text="👀 Просмотреть", callback_data=f"view_draft:{draft.id}"),
                types.InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_draft:{draft.id}")
            )
            builder.row(
                types.InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_draft_admin:{draft.id}"),
                types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_draft:{draft.id}")
            )
            
            draft_text = (
                f"🆔 *Черновик #{draft.id}*\n"
                f"👤 Пользователь: {draft.first_name or 'Неизвестно'} (@{draft.username or 'нет'})\n"
                f"❓ Вопрос: {draft.question[:200]}..."
            )
            await message.answer(draft_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("view_draft:"))
async def handle_view_draft(callback: CallbackQuery):
    """Просмотр деталей черновика"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.get_draft_by_id(session, draft_id)
        
        if not draft:
            await callback.answer("❌ Черновик не найден.", show_alert=True)
            return
        
        details = (
            f"📋 *Детали черновика #{draft.id}*\n\n"
            f"👤 *Пользователь:*\n"
            f"• ID: {draft.user_id}\n"
            f"• Имя: {draft.first_name or 'Неизвестно'}\n"
            f"• Username: @{draft.username or 'нет'}\n\n"
            f"❓ *Вопрос:*\n{draft.question}\n\n"
            f"🤖 *Черновик ИИ:*\n{draft.ai_draft[:2000]}"
        )
        if len(draft.ai_draft) > 2000:
            details += "\n... (текст обрезан)"
        
        details += f"\n\n📊 *Статус:* {draft.status.value}"
        if draft.reviewer_id:
            details += f"\n👨‍💼 *Проверяющий:* {draft.reviewer_id}"
        if draft.reviewer_notes:
            details += f"\n📝 *Заметки проверяющего:*\n{draft.reviewer_notes}"
        
        details += f"\n\n🕒 *Создан:* {draft.created_at.strftime('%d.%m.%Y %H:%M')}"
        if draft.reviewed_at:
            details += f"\n✏️ *Проверен:* {draft.reviewed_at.strftime('%d.%m.%Y %H:%M')}"
        
        await callback.answer()
        await callback.message.answer(details, parse_mode="Markdown")


@router.callback_query(lambda c: c.data.startswith("approve_draft:"))
async def handle_approve_draft(callback: CallbackQuery):
    """Одобрение черновика (отправка как есть)"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.approve_draft(
            session=session,
            draft_id=draft_id,
            reviewer_id=callback.from_user.id,
            final_answer=None,  # отправляем как есть
            reviewer_notes="Одобрено без изменений."
        )
        
        if not draft:
            await callback.answer("❌ Черновик не найден.", show_alert=True)
            return
        
        # Отправляем ответ пользователю
        try:
            await callback.bot.send_message(
                chat_id=draft.user_id,
                text=f"✅ *Ваш черновик проверен*\n\n{draft.final_answer}",
                parse_mode="Markdown"
            )
            # Помечаем как отправленный
            await HybridDraftService.mark_as_sent(session, draft_id)
            await callback.answer("✅ Черновик одобрен и отправлен пользователю.")
            
            # Обновляем сообщение
            await callback.message.edit_text(
                f"✅ *Черновик #{draft_id} одобрен и отправлен пользователю.*",
                parse_mode="Markdown"
            )
        except Exception as e:
            log.error(f"Ошибка при отправке черновика пользователю: {e}")
            await callback.answer("✅ Черновик одобрен, но не удалось отправить пользователю.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("edit_draft_admin:"))
async def handle_edit_draft_admin(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования черновика администратором"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    # Сохраняем draft_id в состоянии
    await state.update_data(admin_edit_draft_id=draft_id)
    await callback.answer()
    
    await callback.message.answer(
        f"✏️ *Редактирование черновика #{draft_id}*\n\n"
        "Отправьте исправленный текст ответа. Вы можете полностью изменить текст или отредактировать частично.\n\n"
        "Когда закончите — просто отправьте сообщение.",
        parse_mode="Markdown"
    )


@router.message(F.text & F.from_user.id == settings.ADMIN_USER_ID)
async def handle_admin_edited_draft(message: Message, state: FSMContext):
    """Обработчик отредактированного черновика администратором"""
    data = await state.get_data()
    draft_id = data.get("admin_edit_draft_id")
    
    if not draft_id:
        # Не редактируем черновик, возможно это другое сообщение
        return
    
    edited_text = message.text.strip()
    if not edited_text:
        await message.answer("❌ Текст не может быть пустым.")
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.approve_draft(
            session=session,
            draft_id=draft_id,
            reviewer_id=message.from_user.id,
            final_answer=edited_text,
            reviewer_notes="Отредактировано администратором."
        )
        
        if not draft:
            await message.answer("❌ Черновик не найден.")
            await state.clear()
            return
        
        # Отправляем ответ пользователю
        try:
            await message.bot.send_message(
                chat_id=draft.user_id,
                text=f"✅ *Ваш черновик проверен и отредактирован*\n\n{draft.final_answer}",
                parse_mode="Markdown"
            )
            # Помечаем как отправленный
            await HybridDraftService.mark_as_sent(session, draft_id)
            await message.answer(f"✅ Черновик #{draft_id} отредактирован и отправлен пользователю.")
        except Exception as e:
            log.error(f"Ошибка при отправке черновика пользователю: {e}")
            await message.answer("✅ Черновик отредактирован, но не удалось отправить пользователю.")
    
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("reject_draft:"))
async def handle_reject_draft(callback: CallbackQuery, state: FSMContext):
    """Отклонение черновика"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Доступ запрещён.", show_alert=True)
        return
    
    try:
        draft_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка формата.", show_alert=True)
        return
    
    # Сохраняем draft_id в состоянии и просим причину отклонения
    await state.update_data(admin_reject_draft_id=draft_id)
    await callback.answer()
    
    await callback.message.answer(
        f"❌ *Отклонение черновика #{draft_id}*\n\n"
        "Укажите причину отклонения (это будет сохранено в заметках):",
        parse_mode="Markdown"
    )


@router.message(F.text & F.from_user.id == settings.ADMIN_USER_ID)
async def handle_admin_reject_reason(message: Message, state: FSMContext):
    """Обработчик причины отклонения черновика"""
    data = await state.get_data()
    draft_id = data.get("admin_reject_draft_id")
    
    if not draft_id:
        # Не отклоняем черновик, возможно это другое сообщение
        return
    
    reason = message.text.strip()
    if not reason:
        await message.answer("❌ Причина не может быть пустой.")
        return
    
    async with get_session_maker()() as session:
        draft = await HybridDraftService.reject_draft(
            session=session,
            draft_id=draft_id,
            reviewer_id=message.from_user.id,
            reviewer_notes=reason
        )
        
        if not draft:
            await message.answer("❌ Черновик не найден.")
            await state.clear()
            return
        
        # Уведомляем пользователя об отклонении
        try:
            await message.bot.send_message(
                chat_id=draft.user_id,
                text=f"❌ *Ваш черновик отклонён*\n\n"
                     f"Причина: {reason}\n\n"
                     f"Вы можете задать новый вопрос или отредактировать существующий.",
                parse_mode="Markdown"
            )
            await message.answer(f"✅ Черновик #{draft_id} отклонён. Пользователь уведомлён.")
        except Exception as e:
            log.error(f"Ошибка при уведомлении пользователя: {e}")
            await message.answer(f"✅ Черновик #{draft_id} отклонён, но не удалось уведомить пользователя.")
    
    await state.clear()