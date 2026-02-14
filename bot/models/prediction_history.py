"""
Модель для истории предсказаний (таро, руны, гороскопы, нумерология и т.д.)
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base

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
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)  # ID пользователя Telegram
    prediction_type = Column(Enum(PredictionType), nullable=False)  # Тип предсказания
    subtype = Column(String(100), nullable=True)  # Подтип (например, "daily", "weekly", "one_card", "three_cards")
    details = Column(JSON, nullable=True)  # Детали предсказания в формате JSON
    result_text = Column(Text, nullable=False)  # Текст результата предсказания
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # Дата создания
    
    # Дополнительные поля для контекста
    user_message = Column(Text, nullable=True)  # Сообщение пользователя (если было)
    username = Column(String(100), nullable=True)  # Username пользователя для удобства
    first_name = Column(String(100), nullable=True)  # Имя пользователя для удобства
    
    def __repr__(self):
        return f"<PredictionHistory(id={self.id}, user_id={self.user_id}, type={self.prediction_type.value})>"
    
    def to_dict(self):
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