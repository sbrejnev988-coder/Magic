"""
РњРѕРґРµР»СЊ РїСЂРѕС„РёР»СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РґР»СЏ РїРµСЂСЃРѕРЅР°Р»РёР·Р°С†РёРё РїСЂРѕРјРїС‚РѕРІ.
РҐСЂР°РЅРёС‚ РїРµСЂСЃРѕРЅР°Р»СЊРЅС‹Рµ РґР°РЅРЅС‹Рµ: РёРјСЏ, Р·РЅР°Рє Р·РѕРґРёР°РєР°, РІРѕР·СЂР°СЃС‚, РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ РїСЂРµРґРїРѕС‡С‚РµРЅРёСЏ.
"""

from datetime import datetime
from sqlalchemy import Integer, BigInteger, String, DateTime, Text, Boolean, Enum, func
from sqlalchemy.orm import Mapped, mapped_column
import enum

from .base import Base


class ZodiacSign(enum.Enum):
    ARIES = "aries"
    TAURUS = "taurus"
    GEMINI = "gemini"
    CANCER = "cancer"
    LEO = "leo"
    VIRGO = "virgo"
    LIBRA = "libra"
    SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"
    CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"
    PISCES = "pisces"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    zodiac_sign: Mapped[ZodiacSign] = mapped_column(Enum(ZodiacSign), nullable=True)
    zodiac_element: Mapped[str] = mapped_column(String(20), nullable=True)  # РѕРіРѕРЅСЊ, Р·РµРјР»СЏ, РІРѕР·РґСѓС…, РІРѕРґР°
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    birth_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    ruling_planet: Mapped[str] = mapped_column(String(50), nullable=True)  # СѓРїСЂР°РІРёС‚РµР»СЊ Р·РЅР°РєР°
    preferred_module: Mapped[str] = mapped_column(String(50), nullable=True)  # Р»СЋР±РёРјС‹Р№ РјРѕРґСѓР»СЊ (tarot, numerology...)
    personal_notes: Mapped[str] = mapped_column(Text, nullable=True)  # РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹Рµ Р·Р°РјРµС‚РєРё
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # СЂР°Р·СЂРµС€РёС‚СЊ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ РґР°РЅРЅС‹Рµ РІ РїСЂРѕРјРїС‚Р°С…
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserProfile user_id={self.user_id} name={self.first_name} sign={self.zodiac_sign}>"

    @property
    def full_name(self) -> str:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ РїРѕР»РЅРѕРµ РёРјСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else "РќРµРёР·РІРµСЃС‚РЅС‹Р№"

    def to_prompt_context(self) -> dict:
        """Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃР»РѕРІР°СЂСЊ СЃ РґР°РЅРЅС‹РјРё РґР»СЏ РїРѕРґСЃС‚Р°РЅРѕРІРєРё РІ РїСЂРѕРјРїС‚."""
        return {
            "user_name": self.full_name,
            "first_name": self.first_name or "РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ",
            "zodiac_sign": self.zodiac_sign.value if self.zodiac_sign else "РЅРµРёР·РІРµСЃС‚РµРЅ",
            "zodiac_element": self.zodiac_element or "РЅРµРёР·РІРµСЃС‚РЅР°",
            "age": self.age or "РЅРµ СѓРєР°Р·Р°РЅ",
            "ruling_planet": self.ruling_planet or "РЅРµ СѓРєР°Р·Р°РЅ",
            "preferred_module": self.preferred_module or "РЅРµ СѓРєР°Р·Р°РЅ",
        }