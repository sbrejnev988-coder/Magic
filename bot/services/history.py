"""
Сервис для работы с историей консультаций.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from bot.models.consultation import Consultation

logger = logging.getLogger(__name__)


class ConsultationHistory:
    """Управление историей консультаций."""
    
    @staticmethod
    async def add(
        session: AsyncSession,
        user_id: int,
        question: str,
        answer: str
    ) -> Consultation:
        """Добавить консультацию в историю."""
        consultation = Consultation(
            user_id=user_id,
            question=question,
            answer=answer,
            created_at=datetime.utcnow()
        )
        session.add(consultation)
        await session.commit()
        await session.refresh(consultation)
        logger.debug(f"Консультация сохранена для пользователя {user_id}")
        return consultation
    
    @staticmethod
    async def get_by_user(
        session: AsyncSession,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> List[Consultation]:
        """Получить историю консультаций пользователя."""
        stmt = (
            select(Consultation)
            .where(Consultation.user_id == user_id)
            .order_by(desc(Consultation.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        consultations = result.scalars().all()
        return consultations
    
    @staticmethod
    async def get_recent(
        session: AsyncSession,
        user_id: int,
        count: int = 3
    ) -> List[Consultation]:
        """Получить последние N консультаций пользователя."""
        return await ConsultationHistory.get_by_user(session, user_id, limit=count)
    
    @staticmethod
    async def delete(
        session: AsyncSession,
        consultation_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """Удалить консультацию (только свою)."""
        stmt = select(Consultation).where(Consultation.id == consultation_id)
        if user_id is not None:
            stmt = stmt.where(Consultation.user_id == user_id)
        
        result = await session.execute(stmt)
        consultation = result.scalar_one_or_none()
        
        if consultation is None:
            return False
        
        await session.delete(consultation)
        await session.commit()
        return True
    
    @staticmethod
    async def count_by_user(
        session: AsyncSession,
        user_id: int
    ) -> int:
        """Получить общее количество консультаций пользователя."""
        stmt = select(Consultation).where(Consultation.user_id == user_id)
        result = await session.execute(stmt)
        count = result.scalars().all()
        return len(count)