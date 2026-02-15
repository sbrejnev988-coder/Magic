#!/usr/bin/env python3
"""
Скрипт для одновременного запуска всех ботов MysticBot.
Запускает:
1. Основной бот (bot/main.py)
2. Бот-консультант (admin_bot.py)

Использование:
    python run_bots.py          # запуск в консоли
    python run_bots.py --daemon # запуск в фоне (демон)
"""

import asyncio
import subprocess
import sys
import os
import signal
import time
from pathlib import Path
import logging

# Загрузка переменных окружения из .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Настройка логирования (будет выполнена после создания папки logs)
logger = None  # будет инициализирован в setup_logging

def setup_logging():
    """Инициализация логирования после создания папки logs"""
    global logger
    # Убедимся, что папка logs существует
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("logs/bots_launcher.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logger = logging.getLogger("bots_launcher")

# Пути к скриптам ботов
MAIN_BOT_SCRIPT = "bot/main.py"
CONSULTANT_BOT_SCRIPT = "admin_bot.py"

# Процессы ботов
processes = []
open_files = []

# Graceful shutdown timeout (секунды)
GRACEFUL_SHUTDOWN_TIMEOUT = 30


def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"Получен сигнал {signum}. Останавливаю ботов...")
    stop_bots()
    sys.exit(0)


def stop_bots():
    """Остановка всех запущенных ботов с graceful shutdown"""
    logger.info("Остановка ботов...")
    
    # Сначала отправляем SIGTERM для graceful shutdown
    for proc in processes:
        if proc and proc.poll() is None:
            logger.info(f"Отправляю SIGTERM процессу {proc.pid}...")
            proc.terminate()
    
    # Ждём graceful shutdown
    start_time = time.time()
    while time.time() - start_time < GRACEFUL_SHUTDOWN_TIMEOUT:
        all_stopped = True
        for proc in processes:
            if proc and proc.poll() is None:
                all_stopped = False
                break
        
        if all_stopped:
            logger.info("Все боты корректно остановлены.")
            break
        
        time.sleep(0.5)
    
    # Принудительно завершаем оставшиеся процессы
    for proc in processes:
        if proc and proc.poll() is None:
            logger.warning(f"Процесс {proc.pid} не остановился за {GRACEFUL_SHUTDOWN_TIMEOUT}с, принудительное завершение...")
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.error(f"Не удалось завершить процесс {proc.pid}")
    
    processes.clear()
    # Закрыть все открытые лог-файлы
    for f in open_files:
        try:
            f.close()
        except Exception:
            pass
    open_files.clear()
    logger.info("Все боты остановлены.")


def check_requirements():
    """Проверка наличия необходимых файлов"""
    required_files = [MAIN_BOT_SCRIPT, CONSULTANT_BOT_SCRIPT, ".env"]
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Отсутствуют необходимые файлы: {missing_files}")
        logger.info("Убедитесь, что вы находитесь в корневой папке MysticBot.")
        return False
    
    # Папка logs будет создана в setup_logging
    
    return True


def start_bot(script_name, bot_name):
    """Запуск одного бота"""
    log_fd = None
    try:
        logger.info(f"Запускаю {bot_name} ({script_name})...")
        
        # Создаем отдельный лог-файл для этого бота
        log_file = f"logs/{bot_name.lower().replace(' ', '_')}.log"
        
        # Открываем лог-файл для записи (без with, чтобы не закрывать раньше времени)
        log_fd = open(log_file, "a", encoding="utf-8")
        open_files.append(log_fd)
        
        # Запускаем процесс напрямую через файл (исправлено)
        proc = subprocess.Popen(
            [sys.executable, script_name],
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1
        )
        
        processes.append(proc)
        logger.info(f"{bot_name} запущен (PID: {proc.pid}). Логи в {log_file}")
        
        # Дадим процессу немного времени на инициализацию
        time.sleep(2)
        
        # Проверим, не завершился ли процесс с ошибкой
        if proc.poll() is not None:
            logger.error(f"{bot_name} завершился сразу после запуска. Проверьте логи.")
            # Прочитаем последние строки лога для диагностики
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if lines:
                        logger.error(f"Последние строки лога:\n{''.join(lines[-20:])}")
            except:
                pass
            # Закрываем лог-файл, т.к. процесс завершился
            if log_fd:
                log_fd.close()
                open_files.remove(log_fd)
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при запуске {bot_name}: {e}")
        if log_fd:
            log_fd.close()
            if log_fd in open_files:
                open_files.remove(log_fd)
        return False


def start_all_bots(daemon_mode=False):
    """Запуск всех ботов"""
    if not check_requirements():
        return False
    
    logger.info("=" * 60)
    logger.info("ЗАПУСК ВСЕХ БОТОВ MYSTICBOT")
    logger.info("=" * 60)
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запускаем ботов
    bots_to_start = [
        (MAIN_BOT_SCRIPT, "Основной бот"),
        (CONSULTANT_BOT_SCRIPT, "Бот-консультант")
    ]
    
    success_count = 0
    for script, name in bots_to_start:
        if start_bot(script, name):
            success_count += 1
    
    if success_count == 0:
        logger.error("Не удалось запустить ни одного бота.")
        return False
    
    logger.info(f"Успешно запущено {success_count}/{len(bots_to_start)} ботов.")
    
    if daemon_mode:
        logger.info("Режим демона: боты работают в фоне.")
        logger.info("Для остановки используйте Ctrl+C или отправьте SIGTERM.")
        
        # В режиме демона ждём сигнала завершения
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Получен Ctrl+C. Останавливаю ботов...")
            stop_bots()
    
    else:
        logger.info("Боты запущены. Логи выводятся в консоль и файлы в папке logs/.")
        logger.info("Для остановки нажмите Ctrl+C.")
        
        # В интерактивном режиме показываем статус и ждём Ctrl+C
        try:
            while True:
                # Периодически проверяем статус ботов
                time.sleep(10)
                
                alive_count = 0
                for i, proc in enumerate(processes):
                    if proc.poll() is None:
                        alive_count += 1
                    else:
                        bot_name = bots_to_start[i][1]
                        logger.warning(f"{bot_name} завершил работу (код: {proc.returncode}).")
                
                if alive_count == 0:
                    logger.info("Все боты завершили работу.")
                    break
                    
                logger.info(f"Работают ботов: {alive_count}/{len(processes)}")
                
        except KeyboardInterrupt:
            logger.info("\nПолучен Ctrl+C. Останавливаю ботов...")
            stop_bots()
    
    return True


def main():
    """Основная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Запуск всех ботов MysticBot")
    parser.add_argument("--daemon", "-d", action="store_true", 
                       help="Запуск в фоновом режиме (демон)")
    parser.add_argument("--stop", "-s", action="store_true",
                       help="Остановить все запущенные боты")
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.stop:
        # Найдём и остановим все процессы Python, связанные с ботами
        try:
            import psutil
        except ImportError:
            logger.error("Модуль psutil не установлен. Установите: pip install psutil")
            return
        
        current_pid = os.getpid()
        
        logger.info("Поиск процессов ботов...")
        bot_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'python' in proc.info['name'].lower():
                    # Проверяем, связан ли процесс с нашими ботами
                    if any(x in ' '.join(cmdline) for x in ['bot/main', 'admin_bot']):
                        if proc.info['pid'] != current_pid:
                            bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if bot_processes:
            logger.info(f"Найдено {len(bot_processes)} процессов ботов:")
            for proc in bot_processes:
                logger.info(f"  PID {proc.info['pid']}: {' '.join(proc.info['cmdline'][:3])}...")
                proc.terminate()
            
            # Дадим процессам время на graceful shutdown
            logger.info(f"Ожидание graceful shutdown ({GRACEFUL_SHUTDOWN_TIMEOUT}с)...")
            time.sleep(min(GRACEFUL_SHUTDOWN_TIMEOUT, 10))
            
            # Принудительно завершаем оставшиеся
            for proc in bot_processes:
                try:
                    if proc.is_running():
                        proc.kill()
                        logger.info(f"Принудительно завершён PID {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            logger.info("Все процессы ботов остановлены.")
        else:
            logger.info("Процессы ботов не найдены.")
        
        return
    
    # Запуск ботов
    start_all_bots(args.daemon)


if __name__ == "__main__":
    main()
