"""
Модель настроек пользователя для персонализации и уведомлений.
"""

from datetime import datetime, time
from sqlalchemy import Integer, BigInteger, String, Boolean, Time, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserSettings(Base):
    """Настройки пользователя для персонализации и уведомлений."""
    __tablename__ = "user_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    
    # Персонализация
    preferred_language: Mapped[str] = mapped_column(String(10), default="ru")  # ru, en
    preferred_timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    favorite_modules: Mapped[str] = mapped_column(String(500), default="")  # список через запятую: tarot,numerology,horoscope
    ai_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # режим ИИ: все сообщения обрабатываются ИИ
    hybrid_mode: Mapped[bool] = mapped_column(Boolean, default=False)  # гибридный режим: черновик + редактирование
    
    # Уведомления
    enable_daily_notifications: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_time: Mapped[time] = mapped_column(Time, default=time(9, 0))  # 09:00 по умолчанию
    notify_rune_of_day: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_affirmation_of_day: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_horoscope_daily: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_tarot_card_of_day: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_meditation_reminder: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Статистика и активность
    last_active: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    total_consultations: Mapped[int] = mapped_column(Integer, default=0)
    total_files_uploaded: Mapped[int] = mapped_column(Integer, default=0)
    preferences: Mapped[str] = mapped_column(String(1000), default="")  # JSON-строка с дополнительными настройками
    
    # AI режим и ограничения
    daily_ai_requests: Mapped[int] = mapped_column(Integer, default=0)  # количество запросов ИИ за сегодня
    last_ai_request_date: Mapped[datetime] = mapped_column(default=datetime.utcnow)  # дата последнего запроса ИИ
    ai_requests_limit: Mapped[int] = mapped_column(Integer, default=15)  # дневной лимит запросов для платных пользователей
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, language={self.preferred_language})>"
    
    def get_favorite_modules_list(self) -> list[str]:
        """Получить список любимых модулей."""
        if not self.favorite_modules:
            return []
        return [m.strip() for m in self.favorite_modules.split(",") if m.strip()]
    
    def add_favorite_module(self, module: str):
        """Добавить модуль в избранное."""
        modules = self.get_favorite_modules_list()
        if module not in modules:
            modules.append(module)
            self.favorite_modules = ",".join(modules)
    
    def remove_favorite_module(self, module: str):
        """Удалить модуль из избранного."""
        modules = self.get_favorite_modules_list()
        if module in modules:
            modules.remove(module)
            self.favorite_modules = ",".join(modules)
    
    def is_module_favorite(self, module: str) -> bool:
        """Проверить, является ли модуль избранным."""
        return module in self.get_favorite_modules_list()