"""
РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ Р±РѕС‚Р° вЂ” РЅР°СЃС‚СЂРѕР№РєРё РёР· .env
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
    """РќР°СЃС‚СЂРѕР№РєРё РїСЂРёР»РѕР¶РµРЅРёСЏ РёР· РїРµСЂРµРјРµРЅРЅС‹С… РѕРєСЂСѓР¶РµРЅРёСЏ"""

    # Telegram Р±РѕС‚
    BOT_TOKEN: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    ADMIN_BOT_TOKEN: str = field(default_factory=lambda: os.getenv("ADMIN_BOT_TOKEN", ""))
    ADMIN_USER_ID: int = field(default_factory=lambda: int(os.getenv("ADMIN_USER_ID", "0")))
    
    # Telegram Userbot API (for automation)
    TELEGRAM_API_ID: str = field(default_factory=lambda: os.getenv("TELEGRAM_API_ID", ""))
    TELEGRAM_API_HASH: str = field(default_factory=lambda: os.getenv("TELEGRAM_API_HASH", ""))

    # Р‘Р°Р·Р° РґР°РЅРЅС‹С…
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://mystic:mysticpass@localhost/mysticbot")
    )
    REDIS_URL: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )

    # API Keys
    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    PERPLEXITY_API_KEY: str = field(default_factory=lambda: os.getenv("PERPLEXITY_API_KEY", ""))
    FEATHERLESS_API_KEY: str = field(default_factory=lambda: os.getenv("FEATHERLESS_API_KEY", ""))
    
    # LLM Models
    OPENAI_MODEL: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    PERPLEXITY_MODEL: str = field(default_factory=lambda: os.getenv("PERPLEXITY_MODEL", "sonar"))
    FEATHERLESS_MODEL: str = field(default_factory=lambda: os.getenv("FEATHERLESS_MODEL", "deepseek-chat"))
    FEATHERLESS_ENDPOINT: str = field(default_factory=lambda: os.getenv("FEATHERLESS_ENDPOINT", ""))
    FEATHERLESS_BASE_URL: str = field(default_factory=lambda: os.getenv("FEATHERLESS_BASE_URL", ""))
    FEATHERLESS_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("FEATHERLESS_TIMEOUT", "180")))
    FEATHERLESS_MAX_RETRIES: int = field(default_factory=lambda: int(os.getenv("FEATHERLESS_MAX_RETRIES", "3")))
    FEATHERLESS_MAX_TOKENS: int = field(default_factory=lambda: int(os.getenv("FEATHERLESS_MAX_TOKENS", "4000")))
    FEATHERLESS_MAX_CONTEXT: int = field(default_factory=lambda: int(os.getenv("FEATHERLESS_MAX_CONTEXT", "16000")))

    # РџСѓС‚Рё
    UPLOAD_DIR: str = field(default_factory=lambda: os.getenv("UPLOAD_DIR", "uploads"))
    DATA_DIR: str = field(default_factory=lambda: os.getenv("DATA_DIR", "data"))

    # Rate limiting
    RATE_LIMIT: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT", "30")))
    RATE_WINDOW: int = field(default_factory=lambda: int(os.getenv("RATE_WINDOW", "60")))

    # Р›РѕРіРёСЂРѕРІР°РЅРёРµ
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # РџР»Р°С‚РµР¶Рё
    PAYMENT_CARD_NUMBER: str = field(default_factory=lambda: os.getenv("PAYMENT_CARD_NUMBER", ""))
    PAYMENT_AMOUNT: int = field(default_factory=lambda: int(os.getenv("PAYMENT_AMOUNT", "777")))

    # Р¤СѓРЅРєС†РёРѕРЅР°Р»СЊРЅРѕСЃС‚СЊ (РІРєР»СЋС‡РµРЅРёРµ/РІС‹РєР»СЋС‡РµРЅРёРµ РјРѕРґСѓР»РµР№)
    ENABLE_TAROT: bool = field(default_factory=lambda: os.getenv("ENABLE_TAROT", "true").lower() == "true")
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

    def __post_init__(self):
        """Р’Р°Р»РёРґР°С†РёСЏ РєРѕРЅС„РёРіСѓСЂР°С†РёРё РїРѕСЃР»Рµ РёРЅРёС†РёР°Р»РёР·Р°С†РёРё"""
        errors = []
        
        # РљСЂРёС‚РёС‡РµСЃРєРёРµ РїР°СЂР°РјРµС‚СЂС‹
        if not self.BOT_TOKEN or self.BOT_TOKEN == "":
            errors.append("BOT_TOKEN РЅРµ СѓРєР°Р·Р°РЅ. РЈРєР°Р¶РёС‚Рµ РµРіРѕ РІ .env С„Р°Р№Р»Рµ.")
        
        if self.ADMIN_USER_ID == 0:
            errors.append("ADMIN_USER_ID РЅРµ СѓРєР°Р·Р°РЅ. РЈРєР°Р¶РёС‚Рµ РµРіРѕ РІ .env С„Р°Р№Р»Рµ.")
        
        # РџСЂРѕРІРµСЂРєР° С„РѕСЂРјР°С‚Р° API РєР»СЋС‡РµР№
        if self.OPENAI_API_KEY and not self.OPENAI_API_KEY.startswith("sk-"):
            errors.append("РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ С„РѕСЂРјР°С‚ OPENAI_API_KEY. Р”РѕР»Р¶РµРЅ РЅР°С‡РёРЅР°С‚СЊСЃСЏ СЃ 'sk-'")
        
        if self.PERPLEXITY_API_KEY and not self.PERPLEXITY_API_KEY.startswith("pplx-"):
            errors.append("РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ С„РѕСЂРјР°С‚ PERPLEXITY_API_KEY. Р”РѕР»Р¶РµРЅ РЅР°С‡РёРЅР°С‚СЊСЃСЏ СЃ 'pplx-'")
        
        if self.FEATHERLESS_API_KEY and not self.FEATHERLESS_API_KEY.startswith("rc_"):
            errors.append("РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ С„РѕСЂРјР°С‚ FEATHERLESS_API_KEY. Р”РѕР»Р¶РµРЅ РЅР°С‡РёРЅР°С‚СЊСЃСЏ СЃ 'rc_'")
        
        # Р’Р°Р»РёРґР°С†РёСЏ Featherless base_url Рё РјРѕРґРµР»Рё
        if self.FEATHERLESS_API_KEY:
            # РћРїСЂРµРґРµР»РµРЅРёРµ base_url: РїСЂРёРѕСЂРёС‚РµС‚ Сѓ FEATHERLESS_BASE_URL
            if self.FEATHERLESS_BASE_URL:
                if not self.FEATHERLESS_BASE_URL.endswith("/v1"):
                    errors.append("FEATHERLESS_BASE_URL РґРѕР»Р¶РµРЅ Р·Р°РєР°РЅС‡РёРІР°С‚СЊСЃСЏ РЅР° /v1 (РЅР°РїСЂРёРјРµСЂ, https://api.featherless.ai/v1)")
            elif self.FEATHERLESS_ENDPOINT:
                # РђРІС‚РѕРјР°С‚РёС‡РµСЃРєРѕРµ РїСЂРµРѕР±СЂР°Р·РѕРІР°РЅРёРµ endpoint РІ base_url (СѓРґР°Р»СЏРµРј /chat/completions)
                if "/chat/completions" in self.FEATHERLESS_ENDPOINT:
                    self.FEATHERLESS_BASE_URL = self.FEATHERLESS_ENDPOINT.replace("/chat/completions", "")
                else:
                    self.FEATHERLESS_BASE_URL = self.FEATHERLESS_ENDPOINT
                if not self.FEATHERLESS_BASE_URL.endswith("/v1"):
                    errors.append("FEATHERLESS_ENDPOINT РґРѕР»Р¶РµРЅ СѓРєР°Р·С‹РІР°С‚СЊ РЅР° Р±Р°Р·РѕРІС‹Р№ URL СЃ /v1")
            else:
                errors.append("Р”Р»СЏ Featherless API С‚СЂРµР±СѓРµС‚СЃСЏ Р»РёР±Рѕ FEATHERLESS_BASE_URL, Р»РёР±Рѕ FEATHERLESS_ENDPOINT")
            
            # РџСЂРѕРІРµСЂРєР° С„РѕСЂРјР°С‚Р° РјРѕРґРµР»Рё (РґРѕР»Р¶РЅР° Р±С‹С‚СЊ РІ С„РѕСЂРјР°С‚Рµ owner/model-name)
            if self.FEATHERLESS_MODEL and "/" not in self.FEATHERLESS_MODEL:
                errors.append(f"РќРµРєРѕСЂСЂРµРєС‚РЅС‹Р№ С„РѕСЂРјР°С‚ FEATHERLESS_MODEL: '{self.FEATHERLESS_MODEL}'. Р”РѕР»Р¶РµРЅ Р±С‹С‚СЊ РІ С„РѕСЂРјР°С‚Рµ owner/model-name (РЅР°РїСЂРёРјРµСЂ, zai-org/GLM-4.7-Flash)")
            
            # РџСЂРѕРІРµСЂРєР° Р»РёРјРёС‚РѕРІ С‚РѕРєРµРЅРѕРІ (Р·Р°С‰РёС‚Р° РѕС‚ Р°Р±СѓР·Р°)
            if self.FEATHERLESS_MAX_TOKENS <= 0:
                errors.append(f"FEATHERLESS_MAX_TOKENS РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕР»РѕР¶РёС‚РµР»СЊРЅС‹Рј С‡РёСЃР»РѕРј, РїРѕР»СѓС‡РµРЅРѕ: {self.FEATHERLESS_MAX_TOKENS}")
            elif self.FEATHERLESS_MAX_TOKENS > 8000:
                errors.append(f"FEATHERLESS_MAX_TOKENS СЃР»РёС€РєРѕРј Р±РѕР»СЊС€РѕР№ ({self.FEATHERLESS_MAX_TOKENS}). Р РµРєРѕРјРµРЅРґСѓРµС‚СЃСЏ РЅРµ Р±РѕР»РµРµ 8000 РґР»СЏ Р·Р°С‰РёС‚С‹ РѕС‚ Р°Р±СѓР·Р°")
            
            if self.FEATHERLESS_MAX_CONTEXT <= 0:
                errors.append(f"FEATHERLESS_MAX_CONTEXT РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕР»РѕР¶РёС‚РµР»СЊРЅС‹Рј С‡РёСЃР»РѕРј, РїРѕР»СѓС‡РµРЅРѕ: {self.FEATHERLESS_MAX_CONTEXT}")
            elif self.FEATHERLESS_MAX_CONTEXT > 32000:
                errors.append(f"FEATHERLESS_MAX_CONTEXT РїСЂРµРІС‹С€Р°РµС‚ РјР°РєСЃРёРјР°Р»СЊРЅС‹Р№ РєРѕРЅС‚РµРєСЃС‚ РјРѕРґРµР»Рё 32K: {self.FEATHERLESS_MAX_CONTEXT}")
            
            if self.FEATHERLESS_MAX_TOKENS > self.FEATHERLESS_MAX_CONTEXT:
                errors.append(f"FEATHERLESS_MAX_TOKENS ({self.FEATHERLESS_MAX_TOKENS}) РЅРµ РјРѕР¶РµС‚ РїСЂРµРІС‹С€Р°С‚СЊ FEATHERLESS_MAX_CONTEXT ({self.FEATHERLESS_MAX_CONTEXT})")
        
        # РџСЂРѕРІРµСЂРєР° DATABASE_URL
        if self.DATABASE_URL and not any(prefix in self.DATABASE_URL for prefix in ["postgresql://", "sqlite://"]):
            errors.append("РќРµРїРѕРґРґРµСЂР¶РёРІР°РµРјС‹Р№ С„РѕСЂРјР°С‚ DATABASE_URL. РџРѕРґРґРµСЂР¶РёРІР°СЋС‚СЃСЏ: postgresql://, sqlite://")
        
        if errors:
            raise ValueError("\n".join(["\nРћС€РёР±РєРё РєРѕРЅС„РёРіСѓСЂР°С†РёРё:"] + errors))

    @property
    def is_llm_configured(self) -> bool:
        """РџСЂРѕРІРµСЂРєР° РЅР°СЃС‚СЂРѕР№РєРё LLM (OpenAI, Perplexity РёР»Рё Featherless)"""
        return bool(self.OPENAI_API_KEY) or bool(self.PERPLEXITY_API_KEY) or bool(self.FEATHERLESS_API_KEY)

    @property
    def llm_providers_order(self) -> List[str]:
        """РџРѕСЂСЏРґРѕРє РїСЂРѕРІР°Р№РґРµСЂРѕРІ LLM РїРѕ РїСЂРёРѕСЂРёС‚РµС‚Сѓ (Р°РєС‚РёРІРЅС‹Рµ)"""
        providers = []
        if self.FEATHERLESS_API_KEY:
            providers.append("featherless")
        if self.PERPLEXITY_API_KEY:
            providers.append("perplexity")
        if self.OPENAI_API_KEY:
            providers.append("openai")
        return providers

    @property
    def is_database_configured(self) -> bool:
        """РџСЂРѕРІРµСЂРєР° РЅР°СЃС‚СЂРѕР№РєРё Р±Р°Р·С‹ РґР°РЅРЅС‹С…"""
        if not self.DATABASE_URL:
            return False
        # РџРѕРґРґРµСЂР¶РёРІР°РµРј PostgreSQL Рё SQLite
        return any(scheme in self.DATABASE_URL for scheme in ("postgresql", "sqlite"))
