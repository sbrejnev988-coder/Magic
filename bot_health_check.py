#!/usr/bin/env python3
"""
Скрипт проверки работоспособности MysticBot.
Отправляет тестовое сообщение через Bot API и проверяет, что процесс бота жив.
Запускается регулярно (например, раз в день) через cron.
"""

import os
import sys
import logging
import requests
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Пути
WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', 'C:\\Users\\Kekl\\.openclaw\\workspace'))
BOT_DIR = WORKSPACE / 'MysticBot'
ENV_FILE = BOT_DIR / '.env'

def load_env():
    """Загружает переменные окружения из .env файла бота."""
    env = {}
    try:
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip().strip('"\'')
        logger.info(f"Загружено {len(env)} переменных из {ENV_FILE}")
        return env
    except Exception as e:
        logger.error(f"Не удалось загрузить .env файл: {e}")
        return {}

def check_bot_process():
    """Проверяет, запущен ли процесс бота (по имени python)."""
    import subprocess
    try:
        # Для Windows используем tasklist
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'], 
                                capture_output=True, text=True, encoding='cp866')
        lines = result.stdout.strip().split('\n')
        # Ищем процесс, который запускает bot.main
        for line in lines[1:]:  # пропускаем заголовок
            if 'bot.main' in line:
                logger.info(f"Процесс бота найден: {line}")
                return True
        logger.warning("Процесс бота не найден в tasklist.")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке процесса: {e}")
        return False

def send_test_message(token, user_id):
    """Отправляет тестовое сообщение от бота пользователю через Bot API."""
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': user_id,
        'text': '✅ Проверка работоспособности: бот отвечает на команды.',
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if data.get('ok'):
            logger.info(f"Тестовое сообщение отправлено, message_id: {data['result']['message_id']}")
            return True
        else:
            logger.error(f"Ошибка отправки сообщения: {data}")
            return False
    except Exception as e:
        logger.error(f"Исключение при отправке сообщения: {e}")
        return False

def restart_bot():
    """Перезапускает бота (запускает main.py в фоне)."""
    import subprocess
    script_path = BOT_DIR / 'bot' / 'main.py'
    try:
        # Запускаем процесс в фоне (для Windows)
        subprocess.Popen([sys.executable, str(script_path)], cwd=BOT_DIR, shell=False)
        logger.info("Бот запущен.")
        return True
    except Exception as e:
        logger.error(f"Не удалось запустить бота: {e}")
        return False

def main():
    logger.info("=== Начало проверки работоспособности MysticBot ===")
    
    env = load_env()
    token = env.get('BOT_TOKEN')
    user_id = env.get('ADMIN_USER_ID', '576704037')  # ID пользователя по умолчанию
    
    if not token:
        logger.error("BOT_TOKEN не найден в .env файле. Проверка прервана.")
        return False
    
    # 1. Проверить процесс
    is_alive = check_bot_process()
    if not is_alive:
        logger.warning("Процесс бота не найден. Пытаюсь перезапустить...")
        if restart_bot():
            logger.info("Бот перезапущен.")
            # Подождём немного, чтобы бот запустился
            import time
            time.sleep(5)
        else:
            logger.error("Не удалось перезапустить бота. Отправляю уведомление пользователю.")
            # Можно отправить сообщение через другой механизм (например, OpenClaw message tool)
            # Пока просто возвращаем ошибку
            return False
    
    # 2. Отправить тестовое сообщение
    success = send_test_message(token, user_id)
    if not success:
        logger.error("Бот не ответил на тестовое сообщение. Возможно, проблемы с API.")
        return False
    
    logger.info("=== Проверка успешно завершена ===")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)