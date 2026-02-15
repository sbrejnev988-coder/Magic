#!/usr/bin/env python3
"""
Проверка состояния MysticBot.
Если бот не отвечает, отправляет уведомление в Telegram.
"""

import psutil
import logging
import sys
import os
from pathlib import Path

# Добавляем путь к модулям бота
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


def is_bot_process_running() -> bool:
    """Проверяет, запущен ли процесс бота."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'bot.main' in ' '.join(cmdline):
                log.info(f"Найден процесс бота: PID {proc.info['pid']}")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            continue
    log.warning("Процесс бота не найден")
    return False


def send_alert(message: str):
    """Отправляет оповещение в Telegram."""
    try:
        import requests

        token = settings.BOT_TOKEN
        chat_id = 576704037  # ID пользователя Максима
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            log.info("Оповещение отправлено")
        else:
            log.error(f"Ошибка отправки оповещения: {response.text}")
    except Exception as e:
        log.error(f"Не удалось отправить оповещение: {e}")


def main():
    """Основная функция проверки."""
    log.info("Проверка состояния MysticBot...")
    
    if is_bot_process_running():
        log.info("✅ Бот работает")
        # Можно дополнительно проверить ответ на команду /heartbeat
        # но пока просто выходим
        sys.exit(0)
    else:
        log.error("❌ Бот не работает")
        alert_message = (
            "⚠️ *MysticBot не отвечает!*\n"
            "Процесс бота не обнаружен. Требуется перезапуск."
        )
        send_alert(alert_message)
        sys.exit(1)


if __name__ == "__main__":
    main()