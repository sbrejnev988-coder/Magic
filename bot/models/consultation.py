"""
Модель для хранения истории консультаций с AI.
"""

from datetime import datetime
from sqlalchemy import Integer, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Consultation(Base):
    """История консультаций пользователя с AI."""
    __tablename__ = "consultations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связь с файлами
    files: Mapped[list["ConsultationFile"]] = relationship(
        "ConsultationFile", 
        back_populates="consultation",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    def __repr__(self) -> str:
        return f"<Consultation(user_id={self.user_id}, question={self.question[:50]}...)>"
