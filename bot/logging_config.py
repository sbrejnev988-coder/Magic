"""
Конфигурация структурированного логирования для MysticBot.

Поддерживает:
- JSON-формат (для production) и человекочитаемый текст (для development).
- Ротация лог-файлов по размеру и времени.
- Отправка логов в stdout/stderr (для Docker) и в файл (опционально).
- Интеграция с настройками из config.settings.
"""

import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

from .config import settings


class JSONFormatter(logging.Formatter):
    """Форматтер для JSON-логов (используется в production)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_entry.update(record.extra)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_level: Optional[str] = None,
    log_json: Optional[bool] = None,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Настраивает глобальное логирование.

    :param log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    :param log_json: Использовать JSON-формат (иначе человекочитаемый текст).
    :param log_file: Путь к файлу для ротации логов (если None — только консоль).
    :param max_bytes: Максимальный размер лог-файла перед ротацией.
    :param backup_count: Количество архивных лог-файлов.
    """
    if log_level is None:
        log_level = settings.log_level
    if log_json is None:
        log_json = os.getenv("LOG_JSON", "false").strip().lower() == "true"

    level = getattr(logging, log_level.upper(), logging.INFO)

    # Определяем форматтер
    if log_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s:%(module)s:%(lineno)d — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Обработчик для stdout (всегда)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(level)

    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(stdout_handler)

    # Файловый обработчик (если указан log_file)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        root_logger.addHandler(file_handler)

    # Настройка библиотечных логгеров: propagate=False + собственные хэндлеры
    lib_level = logging.WARNING
    for lib_name in ("aiogram", "aiohttp", "sqlalchemy"):
        lib_logger = logging.getLogger(lib_name)
        lib_logger.propagate = False
        lib_logger.setLevel(lib_level)
        lib_logger.handlers.clear()
        lib_logger.addHandler(stdout_handler)
        if log_file:
            lib_logger.addHandler(file_handler)

    logging.info(
        "Логирование инициализировано: уровень=%s, json=%s, файл=%s",
        log_level,
        log_json,
        log_file or "отсутствует",
    )


def get_logger(name: str) -> logging.Logger:
    """Сокращение для получения именованного логгера."""
    return logging.getLogger(name)
