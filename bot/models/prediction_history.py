"""
Модель для истории предсказаний (таро, руны, гороскопы, нумерология и т.д.)
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Optional

from sqlalchemy import Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PredictionType(PyEnum):
    """Типы предсказаний"""
    TAROT = "tarot"
    RUNES = "runes"
    HOROSCOPE = "horoscope"
    NUMEROLOGY = "numerology"
    DREAM = "dream"
    RANDOM = "random"
    ASTROLOGY = "astrology"
    MEDITATION = "meditation"
    FINANCE_CALENDAR = "finance_calendar"
    OTHER = "other"


class PredictionHistory(Base):
    """История предсказаний пользователя"""
    __tablename__ = "prediction_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # ID пользователя Telegram
    prediction_type: Mapped[PredictionType] = mapped_column(Enum(PredictionType), nullable=False)  # Тип предсказания
    subtype: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Подтип
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)  # Детали предсказания в формате JSON
    result_text: Mapped[str] = mapped_column(Text, nullable=False)  # Текст результата предсказания
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)  # Дата создания

    # Дополнительные поля для контекста
    user_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Сообщение пользователя (если было)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Username пользователя
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Имя пользователя

    def __repr__(self) -> str:
        return f"<PredictionHistory(id={self.id}, user_id={self.user_id}, type={self.prediction_type.value})>"

    def to_dict(self) -> dict[str, object]:
        """Преобразование в словарь для сериализации"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "prediction_type": self.prediction_type.value,
            "subtype": self.subtype,
            "details": self.details,
            "result_text": self.result_text[:200] + "..." if len(self.result_text) > 200 else self.result_text,
            "created_at": self.created_at.isoformat(),
            "username": self.username,
            "first_name": self.first_name
        }
