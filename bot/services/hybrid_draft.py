"""
Сервис для работы с черновиками гибридного режима.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, and_

from bot.models.hybrid_draft import HybridDraft, DraftStatus

logger = logging.getLogger(__name__)


class HybridDraftService:
    """Сервис управления черновиками гибридного режима"""
    
    @staticmethod
    async def create_draft(
        session: AsyncSession,
        user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        question: str,
        ai_draft: str
    ) -> HybridDraft:
        """Создание нового черновика"""
        draft = HybridDraft(
            user_id=user_id,
            username=username,
            first_name=first_name,
            question=question,
            ai_draft=ai_draft,
            status=DraftStatus.PENDING
        )
        
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
        
        logger.info(f"Создан черновик #{draft.id} для пользователя {user_id}")
        return draft
    
    @staticmethod
    async def get_draft_by_id(session: AsyncSession, draft_id: int) -> Optional[HybridDraft]:
        """Получение черновика по ID"""
        stmt = select(HybridDraft).where(HybridDraft.id == draft_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_pending_drafts(session: AsyncSession, limit: int = 20) -> List[HybridDraft]:
        """Получение черновиков, ожидающих проверки"""
        stmt = (
            select(HybridDraft)
            .where(HybridDraft.status == DraftStatus.PENDING)
            .order_by(HybridDraft.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_drafts_by_user(session: AsyncSession, user_id: int, limit: int = 10) -> List[HybridDraft]:
        """Получение черновиков пользователя"""
        stmt = (
            select(HybridDraft)
            .where(HybridDraft.user_id == user_id)
            .order_by(desc(HybridDraft.created_at))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def approve_draft(
        session: AsyncSession,
        draft_id: int,
        reviewer_id: int,
        final_answer: Optional[str] = None,
        reviewer_notes: Optional[str] = None
    ) -> Optional[HybridDraft]:
        """Одобрение черновика (отправка как есть или с редакцией)"""
        draft = await HybridDraftService.get_draft_by_id(session, draft_id)
        if not draft:
            return None
        
        if final_answer:
            draft.final_answer = final_answer
            draft.status = DraftStatus.EDITED
        else:
            draft.final_answer = draft.ai_draft
            draft.status = DraftStatus.APPROVED
        
        draft.reviewer_id = reviewer_id
        draft.reviewer_notes = reviewer_notes
        draft.reviewed_at = datetime.now()
        
        await session.commit()
        await session.refresh(draft)
        
        logger.info(f"Черновик #{draft_id} одобрен проверяющим {reviewer_id}")
        return draft
    
    @staticmethod
    async def mark_as_sent(session: AsyncSession, draft_id: int) -> Optional[HybridDraft]:
        """Пометка черновика как отправленного пользователю"""
        draft = await HybridDraftService.get_draft_by_id(session, draft_id)
        if not draft:
            return None
        
        draft.status = DraftStatus.SENT
        draft.sent_at = datetime.now()
        
        await session.commit()
        await session.refresh(draft)
        
        logger.info(f"Черновик #{draft_id} помечен как отправленный")
        return draft
    
    @staticmethod
    async def reject_draft(
        session: AsyncSession,
        draft_id: int,
        reviewer_id: int,
        reviewer_notes: str
    ) -> Optional[HybridDraft]:
        """Отклонение черновика"""
        draft = await HybridDraftService.get_draft_by_id(session, draft_id)
        if not draft:
            return None
        
        draft.status = DraftStatus.REJECTED
        draft.reviewer_id = reviewer_id
        draft.reviewer_notes = reviewer_notes
        draft.reviewed_at = datetime.now()
        
        await session.commit()
        await session.refresh(draft)
        
        logger.info(f"Черновик #{draft_id} отклонён проверяющим {reviewer_id}")
        return draft
    
    @staticmethod
    async def delete_draft(session: AsyncSession, draft_id: int) -> bool:
        """Удаление черновика"""
        draft = await HybridDraftService.get_draft_by_id(session, draft_id)
        if not draft:
            return False
        
        await session.delete(draft)
        await session.commit()
        
        logger.info(f"Черновик #{draft_id} удалён")
        return True
    
    @staticmethod
    async def get_statistics(session: AsyncSession) -> dict:
        """Статистика по черновикам"""
        # Общее количество черновиков
        stmt_total = select(HybridDraft)
        result_total = await session.execute(stmt_total)
        total = len(result_total.scalars().all())
        
        # По статусам
        stats = {"total": total, "by_status": {}}
        
        for status in DraftStatus:
            stmt = select(HybridDraft).where(HybridDraft.status == status)
            result = await session.execute(stmt)
            count = len(result.scalars().all())
            stats["by_status"][status.value] = count
        
        return stats