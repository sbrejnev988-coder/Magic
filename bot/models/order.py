"""
Модель заказа консультации.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class OrderStatus(enum.Enum):
    """Статусы заказа"""
    NEW = "new"                # новый заказ
    PROCESSING = "processing"  # в обработке
    COMPLETED = "completed"    # выполнен (консультация отправлена)
    CANCELLED = "cancelled"    # отменён


class Order(Base):
    """Заказ консультации"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)  # ID пользователя Telegram
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # @username
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # имя
    question: Mapped[str] = mapped_column(Text, nullable=False)  # вопрос пользователя
    birth_date: Mapped[str] = mapped_column(String(20), nullable=False)  # дата рождения (ДД.ММ.ГГГГ)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.NEW, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # оплачен ли заказ
    payment_screenshot: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # file_id или путь к скриншоту оплаты
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # заметки администратора
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, user_id={self.user_id}, status={self.status})>"

    def to_dict(self) -> dict[str, object]:
        """Преобразование в словарь для JSON"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "question": self.question,
            "birth_date": self.birth_date,
            "status": self.status.value,
            "is_paid": self.is_paid,
            "payment_screenshot": self.payment_screenshot,
            "admin_notes": self.admin_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
