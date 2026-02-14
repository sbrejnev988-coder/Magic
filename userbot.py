#!/usr/bin/env python3
"""
Telegram Userbot для автоматической проверки платежных скриншотов и мониторинга чатов.
Использует Telethon для работы от имени пользователя.
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from telethon import TelegramClient, events
from telethon.tl.types import Message, MessageMediaPhoto, MessageMediaDocument

from bot.config import Settings
from bot.services.order import OrderService
from bot.database.engine import create_engine, get_session_maker

# Настройки
settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
log = logging.getLogger(__name__)

# EasyOCR (опционально, для распознавания текста)
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    reader = easyocr.Reader(['ru', 'en'], gpu=False)  # CPU режим
except ImportError:
    log.warning("EasyOCR не установлен. OCR-распознавание будет недоступно.")
    EASYOCR_AVAILABLE = False
    reader = None

# Ключевые слова для поиска в платежных скриншотах
PAYMENT_KEYWORDS = [
    'перевод', 'оплата', 'чек', 'платеж', 'сумма', 'руб', '₽', '777',
    'tiнkoff', 'тiнькофф', 'сбербанк', 'альфа', 'втб', 'карта',
    'получатель', 'отправитель', 'банк', 'переведено', 'оплачено'
]

# Чаты для мониторинга (по умолчанию)
MONITOR_CHATS = [
    'Mystictestadminbot',  # Чат для платежных скриншотов
    # Добавьте другие чаты по необходимости
]


class MysticUserbot:
    """Userbot для автоматизации задач MysticBot"""
    
    def __init__(self):
        self.client = None
        self.session_file = "mystic_userbot.session"
        self.engine = None
        self.session_maker = None
        self.running = False
        
        # Проверка конфигурации
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            log.error("TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены в .env")
            raise ValueError("Требуется настройка Telegram API")
    
    async def init_database(self):
        """Инициализация базы данных"""
        try:
            self.engine = create_engine(settings.DATABASE_URL)
            self.session_maker = get_session_maker(self.engine)
            log.info("База данных инициализирована")
        except Exception as e:
            log.error(f"Ошибка инициализации БД: {e}")
            self.engine = None
            self.session_maker = None
    
    async def start(self):
        """Запуск userbot"""
        log.info(f"Запуск MysticUserbot с API ID: {settings.TELEGRAM_API_ID[:5]}...")
        
        # Инициализация БД
        await self.init_database()
        
        # Создаем клиент
        self.client = TelegramClient(
            self.session_file,
            int(settings.TELEGRAM_API_ID),
            settings.TELEGRAM_API_HASH
        )
        
        # Регистрируем обработчики
        self.register_handlers()
        
        # Запускаем
        await self.client.start()
        self.running = True
        
        # Получаем информацию о себе
        me = await self.client.get_me()
        log.info(f"Userbot запущен как @{me.username or me.id}")
        
        # Присоединяемся к мониторингу чатов
        await self.join_monitored_chats()
        
        # Запускаем бесконечный цикл
        await self.run_forever()
    
    async def run_forever(self):
        """Бесконечный цикл работы"""
        log.info("Userbot запущен. Ожидание сообщений...")
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            log.info("Получен сигнал остановки")
        except Exception as e:
            log.error(f"Ошибка в основном цикле: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Остановка userbot"""
        log.info("Остановка MysticUserbot...")
        self.running = False
        if self.client:
            await self.client.disconnect()
        log.info("Userbot остановлен")
    
    def register_handlers(self):
        """Регистрация обработчиков событий"""
        
        @self.client.on(events.NewMessage(incoming=True))
        async def handle_new_message(event: events.NewMessage.Event):
            """Обработка всех новых сообщений"""
            try:
                await self.process_message(event.message)
            except Exception as e:
                log.error(f"Ошибка обработки сообщения: {e}")
        
        @self.client.on(events.MessageEdited(incoming=True))
        async def handle_edited_message(event: events.MessageEdited.Event):
            """Обработка отредактированных сообщений"""
            try:
                await self.process_message(event.message)
            except Exception as e:
                log.error(f"Ошибка обработки отредактированного сообщения: {e}")
    
    async def process_message(self, message: Message):
        """Обработка одного сообщения"""
        # Игнорируем свои сообщения
        if message.out:
            return
        
        chat = await message.get_chat()
        chat_title = chat.title or chat.username or chat.id
        
        log.debug(f"Новое сообщение в {chat_title}: {message.text or 'без текста'}")
        
        # Проверяем, является ли сообщение изображением
        if message.media and isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
            # Проверяем, что это изображение (по MIME-типу или расширению)
            if self.is_image_message(message):
                log.info(f"Обнаружено изображение в {chat_title}")
                await self.process_image(message, chat_title)
        
        # Также можно обрабатывать текстовые сообщения
        if message.text:
            await self.process_text(message, chat_title)
    
    def is_image_message(self, message: Message) -> bool:
        """Проверяет, является ли сообщение изображением"""
        if isinstance(message.media, MessageMediaPhoto):
            return True
        
        if isinstance(message.media, MessageMediaDocument):
            doc = message.media.document
            mime_type = doc.mime_type.lower()
            return mime_type.startswith('image/') or doc.mime_type in ['image/jpeg', 'image/png', 'image/jpg']
        
        return False
    
    async def process_image(self, message: Message, chat_title: str):
        """Обработка изображения (платежного скриншота)"""
        if not EASYOCR_AVAILABLE:
            log.warning("EasyOCR не доступен, пропускаем OCR")
            return
        
        log.info(f"Начинаем обработку изображения из {chat_title}")
        
        try:
            # Скачиваем изображение
            file_path = await self.download_image(message)
            if not file_path:
                return
            
            # Распознаем текст
            extracted_text = await self.extract_text_from_image(file_path)
            
            # Удаляем временный файл
            os.remove(file_path)
            
            if extracted_text:
                log.info(f"Распознанный текст ({len(extracted_text)} символов): {extracted_text[:100]}...")
                
                # Ищем ключевые слова
                found_keywords = self.find_payment_keywords(extracted_text)
                
                if found_keywords:
                    log.info(f"Найдены ключевые слова платежа: {', '.join(found_keywords)}")
                    await self.handle_payment_screenshot(
                        message, extracted_text, found_keywords, chat_title
                    )
                else:
                    log.info("Ключевые слова платежа не найдены")
            else:
                log.info("Текст на изображении не распознан")
                
        except Exception as e:
            log.error(f"Ошибка обработки изображения: {e}")
    
    async def download_image(self, message: Message) -> Optional[str]:
        """Скачивает изображение во временный файл"""
        try:
            # Создаем временную директорию
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            # Скачиваем файл
            file_path = temp_dir / f"payment_{message.id}.jpg"
            await message.download_media(file=str(file_path))
            
            log.debug(f"Изображение скачано: {file_path}")
            return str(file_path)
        except Exception as e:
            log.error(f"Ошибка скачивания изображения: {e}")
            return None
    
    async def extract_text_from_image(self, image_path: str) -> Optional[str]:
        """Извлекает текст из изображения с помощью EasyOCR"""
        try:
            results = reader.readtext(image_path, detail=0, paragraph=True)
            if results:
                return "\n".join(results)
        except Exception as e:
            log.error(f"Ошибка OCR: {e}")
        return None
    
    def find_payment_keywords(self, text: str) -> List[str]:
        """Ищет ключевые слова платежа в тексте"""
        text_lower = text.lower()
        found = []
        for keyword in PAYMENT_KEYWORDS:
            if keyword.lower() in text_lower:
                found.append(keyword)
        return found
    
    async def handle_payment_screenshot(self, message: Message, extracted_text: str, 
                                        keywords: List[str], chat_title: str):
        """Обработка платежного скриншота"""
        if not self.session_maker:
            log.error("База данных не инициализирована")
            return
        
        async with self.session_maker() as session:
            order_service = OrderService(session)
            
            # Пытаемся найти заказ по информации в тексте
            # Можно искать по сумме (777), дате, номеру телефона и т.д.
            
            # Здесь должна быть логика сопоставления скриншота с заказом
            # Пока просто логируем
            
            log.info(f"Платежный скриншот обработан:")
            log.info(f"  Чат: {chat_title}")
            log.info(f"  Сообщение ID: {message.id}")
            log.info(f"  Отправитель: {message.sender_id}")
            log.info(f"  Найдено ключевых слов: {len(keywords)}")
            log.info(f"  Текст: {extracted_text[:200]}...")
            
            # Можно отправить уведомление администратору
            await self.notify_admin(
                f"🔄 Обнаружен платежный скриншот в {chat_title}\n"
                f"Ключевые слова: {', '.join(keywords)}\n"
                f"Текст: {extracted_text[:300]}..."
            )
    
    async def process_text(self, message: Message, chat_title: str):
        """Обработка текстового сообщения"""
        text = message.text.lower()
        
        # Пример: поиск упоминаний бота
        if '@mystic' in text or 'mysticbot' in text:
            log.info(f"Упоминание MysticBot в {chat_title}")
            # Можно отправить автоответ или уведомить администратора
    
    async def notify_admin(self, text: str):
        """Отправляет уведомление администратору"""
        try:
            if settings.ADMIN_USER_ID:
                await self.client.send_message(
                    int(settings.ADMIN_USER_ID),
                    text
                )
                log.debug("Уведомление отправлено администратору")
        except Exception as e:
            log.error(f"Ошибка отправки уведомления: {e}")
    
    async def join_monitored_chats(self):
        """Присоединяется к чатам для мониторинга"""
        for chat_id in MONITOR_CHATS:
            try:
                entity = await self.client.get_entity(chat_id)
                log.info(f"Присоединен к чату: {entity.title or entity.username}")
            except Exception as e:
                log.warning(f"Не удалось присоединиться к {chat_id}: {e}")


async def main():
    """Основная функция запуска"""
    try:
        userbot = MysticUserbot()
        await userbot.start()
    except KeyboardInterrupt:
        log.info("Завершение по запросу пользователя")
    except Exception as e:
        log.error(f"Ошибка запуска userbot: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())