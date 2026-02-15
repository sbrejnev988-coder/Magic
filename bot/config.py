"""
MysticBot — Конфигурация
Загрузка переменных окружения с валидацией и дефолтами.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из корня проекта
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramConfig:
    """Конфигурация Telegram Bot."""
    bot_token: str = ""
    admin_user_id: int = 0


@dataclass(frozen=True)
class DatabaseConfig:
    """Конфигурация базы данных."""
    url: str = "sqlite+aiosqlite:///mysticbot.db"


@dataclass(frozen=True)
class FeatherlessConfig:
    """Конфигурация Featherless AI — основной LLM-провайдер."""
    api_key: str = ""
    base_url: str = "https://api.featherless.ai/v1"
    model: str = "zai-org/GLM-4.7-Flash"
    timeout: int = 180          # секунды (холодный старт модели)
    max_retries: int = 3        # retry при 503
    retry_delay: float = 30.0   # пауза между retry (сек)
    enabled: bool = False


@dataclass(frozen=True)
class PerplexityConfig:
    """Конфигурация Perplexity — фоллбэк #1."""
    api_key: str = ""
    base_url: str = "https://api.perplexity.ai"
    model: str = "sonar-pro"
    timeout: int = 60
    enabled: bool = False


@dataclass(frozen=True)
class OpenAIConfig:
    """Конфигурация OpenAI — фоллбэк #2."""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout: int = 60
    enabled: bool = False


@dataclass(frozen=True)
class FeaturesConfig:
    """Флаги функционала."""
    ai_mode_enabled: bool = True
    hybrid_mode_enabled: bool = True
    daily_ai_limit: int = 50
    enable_tarot: bool = True
    enable_numerology: bool = True
    enable_horoscope: bool = True
    enable_finance_calendar: bool = True
    enable_dream: bool = True
    enable_runes: bool = True
    enable_random: bool = True
    enable_ask: bool = True
    enable_astrology: bool = True
    enable_meditation: bool = True


@dataclass
class Settings:
    """Главный объект настроек — единая точка доступа."""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    featherless: FeatherlessConfig = field(default_factory=FeatherlessConfig)
    perplexity: PerplexityConfig = field(default_factory=PerplexityConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    rate_limit: float = 0.5
    rate_window: int = 1
    redis_url: str = ""
    log_level: str = "INFO"

    @property
    def llm_providers_order(self) -> list[str]:
        """Список активных провайдеров в порядке приоритета."""
        providers = []
        if self.featherless.enabled:
            providers.append("featherless")
        if self.perplexity.enabled:
            providers.append("perplexity")
        if self.openai.enabled:
            providers.append("openai")
        return providers


def _parse_bool(value: str, default: bool = False) -> bool:
    """Парсинг строкового bool из .env."""
    if not value:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


def load_settings() -> Settings:
    """
    Загрузка настроек из переменных окружения.

    Возвращает Settings. Не кидает исключений — 
    при отсутствии ключей провайдер помечается enabled=False.
    """
    warnings: list[str] = []

    # --- Telegram ---
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_raw = os.getenv("ADMIN_USER_ID", "0").strip()

    try:
        admin_user_id = int(admin_id_raw)
    except ValueError:
        admin_user_id = 0
        warnings.append(f"ADMIN_USER_ID='{admin_id_raw}' — не число, установлено 0")

    if not bot_token:
        warnings.append("BOT_TOKEN не указан — бот не сможет запуститься")

    telegram = TelegramConfig(bot_token=bot_token, admin_user_id=admin_user_id)

    # --- Database ---
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///mysticbot.db").strip()
    database = DatabaseConfig(url=db_url)

    # --- Featherless AI ---
    fl_key = os.getenv("FEATHERLESS_API_KEY", "").strip()
    # Поддержка и FEATHERLESS_ENDPOINT (старое), и FEATHERLESS_BASE_URL (новое)
    fl_base = os.getenv(
        "FEATHERLESS_BASE_URL",
        os.getenv("FEATHERLESS_ENDPOINT", "https://api.featherless.ai/v1")
    ).strip().rstrip("/")
    fl_model = os.getenv("FEATHERLESS_MODEL", "zai-org/GLM-4.7-Flash").strip()
    fl_timeout = try:
        int(os.getenv("FEATHERLESS_TIMEOUT", "180"))
    except ValueError:
        # default value? need to decide
        pass
    fl_retries = try:
        int(os.getenv("FEATHERLESS_MAX_RETRIES", "3"))
    except ValueError:
        # default value? need to decide
        pass

    # Валидация base_url
    if fl_key and not fl_base.endswith("/v1"):
        warnings.append(
            f"FEATHERLESS_BASE_URL='{fl_base}' не заканчивается на /v1. "
            f"Правильный формат: https://api.featherless.ai/v1"
        )
    # Валидация модели
    if fl_key and "/" not in fl_model:
        warnings.append(
            f"FEATHERLESS_MODEL='{fl_model}' — нет '/' (HuggingFace формат). "
            f"Пример: zai-org/GLM-4.7-Flash"
        )

    featherless = FeatherlessConfig(
        api_key=fl_key,
        base_url=fl_base,
        model=fl_model,
        timeout=fl_timeout,
        max_retries=fl_retries,
        enabled=bool(fl_key),
    )

    # --- Perplexity ---
    px_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
    px_model = os.getenv("PERPLEXITY_MODEL", "sonar-pro").strip()

    perplexity = PerplexityConfig(
        api_key=px_key,
        model=px_model,
        enabled=bool(px_key),
    )

    # --- OpenAI ---
    oai_key = os.getenv("OPENAI_API_KEY", "").strip()
    oai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    openai_cfg = OpenAIConfig(
        api_key=oai_key,
        model=oai_model,
        enabled=bool(oai_key),
    )

    # --- Features ---
    features = FeaturesConfig(
        ai_mode_enabled=_parse_bool(os.getenv("AI_MODE_ENABLED", "true"), True),
        hybrid_mode_enabled=_parse_bool(os.getenv("HYBRID_MODE_ENABLED", "true"), True),
        daily_ai_limit=try:
            int(os.getenv("DAILY_AI_LIMIT", "50"))
        except ValueError:
            # default value? need to decide
            pass,
        enable_tarot=_parse_bool(os.getenv("ENABLE_TAROT", "true"), True),
        enable_numerology=_parse_bool(os.getenv("ENABLE_NUMEROLOGY", "true"), True),
        enable_horoscope=_parse_bool(os.getenv("ENABLE_HOROSCOPE", "true"), True),
        enable_finance_calendar=_parse_bool(os.getenv("ENABLE_FINANCE_CALENDAR", "true"), True),
        enable_dream=_parse_bool(os.getenv("ENABLE_DREAM", "true"), True),
        enable_runes=_parse_bool(os.getenv("ENABLE_RUNES", "true"), True),
        enable_random=_parse_bool(os.getenv("ENABLE_RANDOM", "true"), True),
        enable_ask=_parse_bool(os.getenv("ENABLE_ASK", "true"), True),
        enable_astrology=_parse_bool(os.getenv("ENABLE_ASTROLOGY", "true"), True),
        enable_meditation=_parse_bool(os.getenv("ENABLE_MEDITATION", "true"), True),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    # Rate limiting and Redis
    rate_limit = try:
        float(os.getenv("RATE_LIMIT", "0.5"))
    except ValueError:
        # default value? need to decide
        pass
    rate_window = try:
        int(os.getenv("RATE_WINDOW", "1"))
    except ValueError:
        # default value? need to decide
        pass
    redis_url = os.getenv("REDIS_URL", "")

    settings = Settings(
        telegram=telegram,
        database=database,
        featherless=featherless,
        perplexity=perplexity,
        openai=openai_cfg,
        features=features,
        rate_limit=rate_limit,
        rate_window=rate_window,
        redis_url=redis_url,
        log_level=log_level,
    )

    # Вывод предупреждений
    for w in warnings:
        logger.warning(f"⚠️ Config: {w}")

    # Итоговый лог
    providers = settings.llm_providers_order
    if providers:
        logger.info(f"✅ LLM провайдеры (приоритет): {' → '.join(providers)}")
    else:
        logger.warning("⚠️ Ни один LLM-провайдер не настроен!")

    return settings


# Синглтон — импортируй settings из любого модуля
settings = load_settings()
