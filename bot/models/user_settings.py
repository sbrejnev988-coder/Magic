"""
РњРѕРґРµР»СЊ РЅР°СЃС‚СЂРѕРµРє РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.
"""

from datetime import datetime, time

from sqlalchemy import Integer, BigInteger, Boolean, String, DateTime, Time, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserSettings(Base):
    """РќР°СЃС‚СЂРѕР№РєРё РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ РґР»СЏ Р±РѕС‚Р°."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)

    # Р РµР¶РёРјС‹ СЂР°Р±РѕС‚С‹
    ai_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hybrid_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Р›РёРјРёС‚С‹ РР
    daily_ai_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_requests_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    last_ai_request_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # РЈРІРµРґРѕРјР»РµРЅРёСЏ
    enable_daily_notifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_time: Mapped[time] = mapped_column(
        Time, default=time(9, 0), nullable=False
    )
    favorite_modules: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    # РЎС‚Р°С‚РёСЃС‚РёРєР°
    total_consultations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_files_uploaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # РњРµС‚Р°РґР°РЅРЅС‹Рµ
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def get_favorite_modules_list(self) -> list[str]:
        """РџРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє РёР·Р±СЂР°РЅРЅС‹С… РјРѕРґСѓР»РµР№."""
        if not self.favorite_modules:
            return []
        return [m.strip() for m in self.favorite_modules.split(",") if m.strip()]

    def set_favorite_modules_list(self, modules: list[str]) -> None:
        """РЈСЃС‚Р°РЅРѕРІРёС‚СЊ СЃРїРёСЃРѕРє РёР·Р±СЂР°РЅРЅС‹С… РјРѕРґСѓР»РµР№."""
        self.favorite_modules = ",".join(modules)

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, ai_mode={self.ai_mode})>"
