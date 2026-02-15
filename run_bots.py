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

from __future__ import annotations

import asyncio
import subprocess
import sys
import os
import signal
import time
from pathlib import Path
import logging
from typing import Optional

# Загрузка переменных окружения из .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("WARNING: python-dotenv не установлен. Выполните: pip install python-dotenv")

# Настройка логирования (будет выполнена после создания папки logs)
logger: Optional[logging.Logger] = None  # будет инициализирован в setup_logging


def setup_logging() -> None:
    """Инициализация логирования после создания папки logs."""
    global logger
    # Убедимся, что папка logs существует
    logs_dir = Path("logs")
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
MAIN_BOT_SCRIPT: str = "bot/main.py"
CONSULTANT_BOT_SCRIPT: str = "admin_bot.py"

# Процессы ботов
processes: list[subprocess.Popen] = []
open_files: list = []

# Graceful shutdown timeout (секунды)
GRACEFUL_SHUTDOWN_TIMEOUT: int = 30


def signal_handler(signum: int, frame) -> None:
    """Обработчик сигналов для корректного завершения."""
    if logger:
        logger.info(f"Получен сигнал {signum}. Останавливаю ботов...")
    stop_bots()
    sys.exit(0)


def stop_bots() -> None:
    """Остановка всех запущенных ботов с graceful shutdown."""
    if logger:
        logger.info("Остановка ботов...")

    # Сначала отправляем SIGTERM для graceful shutdown
    for proc in processes:
        if proc and proc.poll() is None:
            if logger:
                logger.info(f"Отправляю SIGTERM процессу {proc.pid}...")
            try:
                proc.terminate()
            except OSError as e:
                if logger:
                    logger.error(f"Ошибка при отправке SIGTERM процессу {proc.pid}: {e}")

    # Ждём graceful shutdown
    start_time = time.time()
    while time.time() - start_time < GRACEFUL_SHUTDOWN_TIMEOUT:
        all_stopped = all(
            proc is None or proc.poll() is not None
            for proc in processes
        )
        if all_stopped:
            if logger:
                logger.info("Все боты корректно остановлены.")
            break
        time.sleep(0.5)

    # Принудительно завершаем оставшиеся процессы
    for proc in processes:
        if proc and proc.poll() is None:
            if logger:
                logger.warning(
                    f"Процесс {proc.pid} не остановился за "
                    f"{GRACEFUL_SHUTDOWN_TIMEOUT}с, принудительное завершение..."
                )
            try:
                proc.kill()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if logger:
                    logger.error(f"Не удалось завершить процесс {proc.pid}")
            except OSError as e:
                if logger:
                    logger.error(f"Ошибка при завершении процесса {proc.pid}: {e}")

    processes.clear()

    # Закрыть все открытые лог-файлы
    for f in open_files:
        try:
            f.close()
        except Exception:
            pass
    open_files.clear()

    if logger:
        logger.info("Все боты остановлены.")


def check_requirements() -> bool:
    """Проверка наличия необходимых файлов."""
    required_files = [MAIN_BOT_SCRIPT, CONSULTANT_BOT_SCRIPT, ".env"]
    missing_files = [f for f in required_files if not os.path.exists(f)]

    if missing_files:
        if logger:
            logger.error(f"Отсутствуют необходимые файлы: {missing_files}")
            logger.info("Убедитесь, что вы находитесь в корневой папке MysticBot.")
        return False

    return True


def start_bot(script_name: str, bot_name: str) -> bool:
    """Запуск одного бота."""
    log_fd = None
    try:
        if logger:
            logger.info(f"Запускаю {bot_name} ({script_name})...")

        # Создаем отдельный лог-файл для этого бота
        log_file = f"logs/{bot_name.lower().replace(' ', '_')}.log"

        # Открываем лог-файл для записи
        log_fd = open(log_file, "a", encoding="utf-8")  # noqa: SIM115
        open_files.append(log_fd)

        # Запускаем процесс
        proc = subprocess.Popen(
            [sys.executable, script_name],
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1
        )

        processes.append(proc)
        if logger:
            logger.info(f"{bot_name} запущен (PID: {proc.pid}). Логи в {log_file}")

        # Дадим процессу немного времени на инициализацию
        time.sleep(2)

        # Проверим, не завершился ли процесс с ошибкой
        if proc.poll() is not None:
            if logger:
                logger.error(f"{bot_name} завершился сразу после запуска (код: {proc.returncode}).")
                # Прочитаем последние строки лога для диагностики
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            logger.error(
                                f"Последние строки лога {bot_name}:\n"
                                f"{''.join(lines[-20:])}"
                            )
                except OSError as read_err:
                    logger.error(f"Не удалось прочитать лог {log_file}: {read_err}")

            # Закрываем лог-файл, т.к. процесс завершился
            if log_fd:
                log_fd.close()
                if log_fd in open_files:
                    open_files.remove(log_fd)
            return False

        return True

    except FileNotFoundError:
        if logger:
            logger.error(f"Скрипт {script_name} не найден.")
        if log_fd:
            log_fd.close()
            if log_fd in open_files:
                open_files.remove(log_fd)
        return False
    except Exception as e:
        if logger:
            logger.error(f"Ошибка при запуске {bot_name}: {type(e).__name__}: {e}")
        if log_fd:
            log_fd.close()
            if log_fd in open_files:
                open_files.remove(log_fd)
        return False


def start_all_bots(daemon_mode: bool = False) -> bool:
    """Запуск всех ботов."""
    if not check_requirements():
        return False

    if logger:
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
        if logger:
            logger.error("Не удалось запустить ни одного бота.")
        return False

    if logger:
        logger.info(f"Успешно запущено {success_count}/{len(bots_to_start)} ботов.")

    if daemon_mode:
        if logger:
            logger.info("Режим демона: боты работают в фоне.")
            logger.info("Для остановки используйте Ctrl+C или отправьте SIGTERM.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if logger:
                logger.info("Получен Ctrl+C. Останавливаю ботов...")
            stop_bots()
    else:
        if logger:
            logger.info("Боты запущены. Логи выводятся в консоль и файлы в папке logs/.")
            logger.info("Для остановки нажмите Ctrl+C.")

        try:
            while True:
                # Периодически проверяем статус ботов
                time.sleep(10)

                alive_count = 0
                for i, proc in enumerate(processes):
                    if proc.poll() is None:
                        alive_count += 1
                    else:
                        if i < len(bots_to_start) and logger:
                            bot_name = bots_to_start[i][1]
                            logger.warning(
                                f"{bot_name} завершил работу "
                                f"(код: {proc.returncode})."
                            )

                if alive_count == 0:
                    if logger:
                        logger.info("Все боты завершили работу.")
                    break

                if logger:
                    logger.info(f"Работают ботов: {alive_count}/{len(processes)}")

        except KeyboardInterrupt:
            if logger:
                logger.info("\nПолучен Ctrl+C. Останавливаю ботов...")
            stop_bots()

    return True


def stop_running_bots() -> None:
    """Найти и остановить все процессы Python, связанные с ботами."""
    try:
        import psutil
    except ImportError:
        if logger:
            logger.error(
                "Модуль psutil не установлен. "
                "Установите: pip install psutil"
            )
        return

    current_pid = os.getpid()

    if logger:
        logger.info("Поиск процессов ботов...")

    bot_processes: list = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and "python" in proc.info["name"].lower():
                cmd_str = " ".join(cmdline)
                if any(x in cmd_str for x in ["bot/main", "admin_bot"]):
                    if proc.info["pid"] != current_pid:
                        bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if bot_processes:
        if logger:
            logger.info(f"Найдено {len(bot_processes)} процессов ботов:")
        for proc in bot_processes:
            if logger:
                logger.info(
                    f"  PID {proc.info['pid']}: "
                    f"{' '.join(proc.info['cmdline'][:3])}..."
                )
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                if logger:
                    logger.error(f"Не удалось отправить SIGTERM PID {proc.info['pid']}: {e}")

        # Дадим процессам время на graceful shutdown
        if logger:
            logger.info(f"Ожидание graceful shutdown ({GRACEFUL_SHUTDOWN_TIMEOUT}с)...")
        time.sleep(min(GRACEFUL_SHUTDOWN_TIMEOUT, 10))

        # Принудительно завершаем оставшиеся
        for proc in bot_processes:
            try:
                if proc.is_running():
                    proc.kill()
                    if logger:
                        logger.info(f"Принудительно завершён PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if logger:
            logger.info("Все процессы ботов остановлены.")
    else:
        if logger:
            logger.info("Процессы ботов не найдены.")


def main() -> None:
    """Основная функция."""
    import argparse

    parser = argparse.ArgumentParser(description="Запуск всех ботов MysticBot")
    parser.add_argument(
        "--daemon", "-d", action="store_true",
        help="Запуск в фоновом режиме (демон)"
    )
    parser.add_argument(
        "--stop", "-s", action="store_true",
        help="Остановить все запущенные боты"
    )

    args = parser.parse_args()

    setup_logging()

    if args.stop:
        stop_running_bots()
        return

    # Запуск ботов
    start_all_bots(args.daemon)


if __name__ == "__main__":
    main()
