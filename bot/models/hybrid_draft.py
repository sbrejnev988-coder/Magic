"""
Модель для хранения черновиков гибридного режима, требующих проверки человеком.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class DraftStatus(enum.Enum):
    """Статусы черновика"""
    PENDING = "pending"        # ожидает проверки
    APPROVED = "approved"      # проверен и одобрен
    EDITED = "edited"          # проверен и отредактирован
    REJECTED = "rejected"      # отклонён
    SENT = "sent"              # отправлен пользователю


class HybridDraft(Base):
    """Черновик гибридного режима для проверки человеком"""
    __tablename__ = "hybrid_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)  # ID пользователя Telegram
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # @username
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # имя пользователя

    question: Mapped[str] = mapped_column(Text, nullable=False)  # вопрос пользователя
    ai_draft: Mapped[str] = mapped_column(Text, nullable=False)  # черновик, сгенерированный ИИ
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # финальный ответ после проверки

    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus), default=DraftStatus.PENDING, nullable=False)

    reviewer_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # ID проверяющего (администратора)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # заметки проверяющего

    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)  # когда проверен
    sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)  # когда отправлен пользователю

    def __repr__(self) -> str:
        return f"<HybridDraft(id={self.id}, user_id={self.user_id}, status={self.status})>"

    def to_dict(self) -> dict[str, object]:
        """Преобразование в словарь для JSON"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "question": self.question,
            "ai_draft": self.ai_draft,
            "final_answer": self.final_answer,
            "status": self.status.value,
            "reviewer_id": self.reviewer_id,
            "reviewer_notes": self.reviewer_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }
