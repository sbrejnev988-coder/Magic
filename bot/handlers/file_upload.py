"""
Обработчики загрузки файлов клиентов.
"""

import logging
import tempfile
import os
from typing import Optional

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, ContentType
from aiogram.enums import ParseMode

from bot.services.client_files import ClientFilesService
from bot.services.history import ConsultationHistory

router = Router()
log = logging.getLogger(__name__)


async def get_last_consultation_id(session, user_id: int) -> Optional[int]:
    """Получить ID последней консультации пользователя."""
    try:
        consultations = await ConsultationHistory.get_recent(session, user_id, count=1)
        if consultations:
            return consultations[0].id
    except Exception as e:
        log.error(f"Ошибка получения последней консультации: {e}")
    return None


@router.message(Command("upload"))
async def cmd_upload(message: Message):
    """Информация о загрузке файлов."""
    help_text = """
📁 *Загрузка файлов*

Вы можете прикреплять файлы к консультациям с AI.

*Поддерживаемые типы:*
• 📄 Документы: `.txt`, `.doc`, `.docx`, `.pdf`, `.rtf`
• 🖼️ Изображения: `.jpg`, `.png`, `.gif`, `.bmp`, `.webp`

*Как это работает:*
1. Отправьте файл боту (любым способом)
2. Файл сохранится в вашей личной папке
3. Он будет прикреплён к последней консультации с AI
4. Вы сможете просматривать файлы в истории (`/history`)

*Важно:* Файлы хранятся локально и доступны только вам.
"""
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)


@router.message(F.content_type.in_({
    ContentType.DOCUMENT,
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.VOICE
}))
async def handle_file_upload(message: Message, session_maker=None):
    """Обработчик загрузки файлов любого типа."""
    if not session_maker:
        await message.answer(
            "⚠️ *Загрузка файлов временно недоступна*\n"
            "База данных не подключена. Попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    
    try:
        # Определяем тип контента и извлекаем файл
        file_info = None
        original_filename = None
        temp_file_path = None
        
        if message.document:
            file_info = message.document
            original_filename = file_info.file_name
        elif message.photo:
            # Берём фото максимального качества
            file_info = message.photo[-1]
            original_filename = f"photo_{file_info.file_unique_id}.jpg"
        elif message.audio:
            file_info = message.audio
            original_filename = file_info.file_name or f"audio_{file_info.file_unique_id}.mp3"
        elif message.voice:
            file_info = message.voice
            original_filename = f"voice_{file_info.file_unique_id}.ogg"
        elif message.video:
            file_info = message.video
            original_filename = file_info.file_name or f"video_{file_info.file_unique_id}.mp4"
        
        if not file_info:
            await message.answer("❌ Не удалось обработать файл.")
            return
        
        # Скачиваем файл во временное место
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, original_filename)
        
        file = await message.bot.get_file(file_info.file_id)
        await message.bot.download_file(file.file_path, temp_file_path)
        
        log.info(f"Файл загружен: {original_filename} от {user_id}")
        
        # Получаем последнюю консультацию пользователя
        async with session_maker() as session:
            last_consult_id = await get_last_consultation_id(session, user_id)
            
            # Обрабатываем файл
            file_record = await ClientFilesService.process_uploaded_file(
                session=session,
                user_id=user_id,
                consultation_id=last_consult_id if last_consult_id else 0,
                temp_file_path=temp_file_path,
                original_filename=original_filename
            )
            
            # Индексация файлов отключена (пользователь сам указывает, к каким файлам обращаться)
        
        # Формируем ответ
        if file_record:
            file_type_emoji = {
                "document": "📄",
                "image": "🖼️",
                "audio": "🎵",
                "video": "🎬"
            }.get(file_record.file_type, "📎")
            
            response_text = (
                f"{file_type_emoji} *Файл сохранён!*\n\n"
                f"*Название:* {file_record.file_name}\n"
                f"*Тип:* {file_record.file_type}\n"
            )
            
            if last_consult_id:
                response_text += f"*Прикреплён к консультации:* #{last_consult_id}\n"
            else:
                response_text += "*Примечание:* Файл сохранён, но не прикреплён к консультации.\n"
            
            response_text += (
                f"\n📂 Файл сохранён в вашей личной папке.\n"
                f"Просмотреть можно в истории (`/history`)."
            )
            
            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN)
        else:
            await message.answer(
                "❌ *Не удалось сохранить файл*\n"
                "Попробуйте позже или обратитесь к администратору.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Очистка временного файла
        try:
            os.remove(temp_file_path)
            os.rmdir(temp_dir)
        except Exception as e:
            log.warning(f"Не удалось очистить временные файлы: {e}")
            
    except Exception as e:
        log.error(f"Ошибка обработки файла: {e}", exc_info=True)
        await message.answer(
            "⚠️ *Ошибка при обработке файла*\n"
            "Попробуйте позже или обратитесь к администратору.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Очистка временных файлов при ошибке
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                if os.path.exists(os.path.dirname(temp_file_path)):
                    os.rmdir(os.path.dirname(temp_file_path))
            except Exception as cleanup_e:
                log.warning(f"Ошибка очистки временных файлов: {cleanup_e}")


@router.message(Command("myfiles"))
async def cmd_myfiles(message: Message, session_maker=None):
    """Показать файлы пользователя."""
    if not session_maker:
        await message.answer(
            "⚠️ *Просмотр файлов временно недоступен*",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    user_id = message.from_user.id
    
    try:
        async with session_maker() as session:
            # Получаем последние 5 консультаций с файлами
            consultations = await ConsultationHistory.get_recent(session, user_id, count=5)
            
            if not consultations:
                await message.answer(
                    "📭 *Нет файлов*\n"
                    "У вас ещё нет сохранённых файлов.\n"
                    "Отправьте файл боту для загрузки.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            files_count = 0
            response_text = "📁 *Ваши файлы:*\n\n"
            
            for consult in consultations:
                files = await ClientFilesService.get_files_for_consultation(
                    session, consult.id, user_id
                )
                
                if files:
                    files_count += len(files)
                    date_str = consult.created_at.strftime("%d.%m.%Y")
                    response_text += f"*Консультация от {date_str}:*\n"
                    
                    for file in files:
                        file_type_emoji = {
                            "document": "📄",
                            "image": "🖼️",
                            "audio": "🎵",
                            "video": "🎬"
                        }.get(file.file_type, "📎")
                        
                        response_text += f"  {file_type_emoji} {file.file_name}\n"
                    
                    response_text += "\n"
            
            if files_count == 0:
                await message.answer(
                    "📭 *Нет файлов*\n"
                    "У вас ещё нет сохранённых файлов.\n"
                    "Отправьте файл боту для загрузки.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            response_text += f"📊 *Всего файлов:* {files_count}\n"
            response_text += "_Файлы хранятся в вашей личной папке._"
            
            await message.answer(response_text, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        log.error(f"Ошибка при получении файлов: {e}")
        await message.answer(
            "⚠️ *Ошибка при загрузке списка файлов*",
            parse_mode=ParseMode.MARKDOWN
        )