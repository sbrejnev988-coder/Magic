"""
Модель настроек пользователя.
"""

from datetime import datetime, time

from sqlalchemy import Integer, BigInteger, Boolean, String, DateTime, Time, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserSettings(Base):
    """Настройки пользователя для бота."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)

    # Режимы работы
    ai_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hybrid_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Лимиты ИИ
    daily_ai_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_requests_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    last_ai_request_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Уведомления
    enable_daily_notifications: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_time: Mapped[time] = mapped_column(
        Time, default=time(9, 0), nullable=False
    )
    favorite_modules: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    # Статистика
    total_consultations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_files_uploaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Метаданные
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
        """Получить список избранных модулей."""
        if not self.favorite_modules:
            return []
        return [m.strip() for m in self.favorite_modules.split(",") if m.strip()]

    def set_favorite_modules_list(self, modules: list[str]) -> None:
        """Установить список избранных модулей."""
        self.favorite_modules = ",".join(modules)

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, ai_mode={self.ai_mode})>"
