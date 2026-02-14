"""
Конфигурация бота — настройки из .env
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

# Safe dotenv loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass
class Settings:
    """Настройки приложения из переменных окружения"""

    # Telegram бот
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_BOT_TOKEN: str = field(default_factory=lambda: os.getenv("ADMIN_BOT_TOKEN", ""))
    ADMIN_USER_ID: int = field(default_factory=lambda: int(os.getenv("ADMIN_USER_ID", "576704037")))
    
    # Telegram Userbot API (for automation)
    TELEGRAM_API_ID: str = field(default_factory=lambda: os.getenv("TELEGRAM_API_ID", ""))
    TELEGRAM_API_HASH: str = field(default_factory=lambda: os.getenv("TELEGRAM_API_HASH", ""))

    # База данных
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://mystic:mysticpass@localhost/mysticbot")
    )
    REDIS_URL: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )

    # API Keys
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    PERPLEXITY_API_KEY: str = field(default_factory=lambda: os.getenv("PERPLEXITY_API_KEY", ""))

    # Пути
    UPLOAD_DIR: str = field(default_factory=lambda: os.getenv("UPLOAD_DIR", "uploads"))
    DATA_DIR: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))

    # Rate limiting
    RATE_LIMIT: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT", "30")))
    RATE_WINDOW: int = field(default_factory=lambda: int(os.getenv("RATE_WINDOW", "60")))

    # Логирование
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Функциональность (включение/выключение модулей)
    ENABLE_TAROT: bool = field(default_factory=lambda: os.getenv("ENABLE_TAROT", "true").lower() == "true")
    ENABLE_PALMISTRY: bool = field(default_factory=lambda: os.getenv("ENABLE_PALMISTRY", "false").lower() == "true")
    ENABLE_NUMEROLOGY: bool = field(default_factory=lambda: os.getenv("ENABLE_NUMEROLOGY", "true").lower() == "true")
    ENABLE_HOROSCOPE: bool = field(default_factory=lambda: os.getenv("ENABLE_HOROSCOPE", "true").lower() == "true")
    ENABLE_FINANCE_CALENDAR: bool = field(
        default_factory=lambda: os.getenv("ENABLE_FINANCE_CALENDAR", "true").lower() == "true"
    )
    ENABLE_DREAM: bool = field(
        default_factory=lambda: os.getenv("ENABLE_DREAM", "true").lower() == "true"
    )
    ENABLE_RUNES: bool = field(
        default_factory=lambda: os.getenv("ENABLE_RUNES", "true").lower() == "true"
    )
    ENABLE_RANDOM: bool = field(
        default_factory=lambda: os.getenv("ENABLE_RANDOM", "true").lower() == "true"
    )
    ENABLE_ASK: bool = field(
        default_factory=lambda: os.getenv("ENABLE_ASK", "true").lower() == "true"
    )
    ENABLE_ASTROLOGY: bool = field(
        default_factory=lambda: os.getenv("ENABLE_ASTROLOGY", "true").lower() == "true"
    )
    ENABLE_MEDITATION: bool = field(
        default_factory=lambda: os.getenv("ENABLE_MEDITATION", "true").lower() == "true"
    )

    @property
    def is_llm_configured(self) -> bool:
        """Проверка настройки LLM (OpenAI или Perplexity)"""
        return bool(self.OPENAI_API_KEY) or bool(self.PERPLEXITY_API_KEY)

    @property
    def is_database_configured(self) -> bool:
        """Проверка настройки базы данных"""
        if not self.DATABASE_URL:
            return False
        # Поддерживаем PostgreSQL и SQLite
        return any(scheme in self.DATABASE_URL for scheme in ("postgresql", "sqlite"))