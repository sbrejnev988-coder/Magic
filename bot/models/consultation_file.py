"""
Модель для прикреплённых файлов к консультациям.
"""

from datetime import datetime
from sqlalchemy import Integer, BigInteger, Text, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ConsultationFile(Base):
    """Файлы, прикреплённые к консультациям."""
    __tablename__ = "consultation_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consultation_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("consultations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'document', 'image', 'audio'
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связь с консультацией
    consultation: Mapped["Consultation"] = relationship("Consultation", back_populates="files")
    
    def __repr__(self) -> str:
        return f"<ConsultationFile(user_id={self.user_id}, file_name={self.file_name})>"
