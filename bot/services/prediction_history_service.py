"""
Сервис для работы с историей предсказаний.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, func

from bot.models.prediction_history import PredictionHistory, PredictionType

logger = logging.getLogger(__name__)


class PredictionHistoryService:
    """Сервис управления историей предсказаний"""
    
    @staticmethod
    async def create_prediction(
        session: AsyncSession,
        user_id: int,
        prediction_type: PredictionType,
        result_text: str,
        subtype: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> PredictionHistory:
        """Создание записи в истории предсказаний"""
        prediction = PredictionHistory(
            user_id=user_id,
            prediction_type=prediction_type,
            subtype=subtype,
            details=details,
            result_text=result_text,
            user_message=user_message,
            username=username,
            first_name=first_name,
        )
        session.add(prediction)
        await session.commit()
        await session.refresh(prediction)
        logger.info(f"Создана запись истории предсказаний #{prediction.id} для пользователя {user_id}, тип: {prediction_type.value}")
        return prediction
    
    @staticmethod
    async def get_by_id(session: AsyncSession, prediction_id: int) -> Optional[PredictionHistory]:
        """Получить запись по ID"""
        stmt = select(PredictionHistory).where(PredictionHistory.id == prediction_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_user(
        session: AsyncSession, 
        user_id: int, 
        limit: int = 20,
        offset: int = 0
    ) -> List[PredictionHistory]:
        """Получить историю предсказаний пользователя"""
        stmt = (
            select(PredictionHistory)
            .where(PredictionHistory.user_id == user_id)
            .order_by(desc(PredictionHistory.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_type(
        session: AsyncSession,
        user_id: int,
        prediction_type: PredictionType,
        limit: int = 20
    ) -> List[PredictionHistory]:
        """Получить историю предсказаний пользователя по типу"""
        stmt = (
            select(PredictionHistory)
            .where(
                and_(
                    PredictionHistory.user_id == user_id,
                    PredictionHistory.prediction_type == prediction_type
                )
            )
            .order_by(desc(PredictionHistory.created_at))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_recent_predictions(
        session: AsyncSession,
        limit: int = 50
    ) -> List[PredictionHistory]:
        """Получить последние предсказания всех пользователей"""
        stmt = (
            select(PredictionHistory)
            .order_by(desc(PredictionHistory.created_at))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def count_by_user(session: AsyncSession, user_id: int) -> int:
        """Подсчитать количество предсказаний пользователя"""
        stmt = select(func.count(PredictionHistory.id)).where(PredictionHistory.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar() or 0
    
    @staticmethod
    async def count_by_type(session: AsyncSession, prediction_type: PredictionType) -> int:
        """Подсчитать количество предсказаний по типу"""
        stmt = select(func.count(PredictionHistory.id)).where(PredictionHistory.prediction_type == prediction_type)
        result = await session.execute(stmt)
        return result.scalar() or 0
    
    @staticmethod
    async def get_today_predictions_count(session: AsyncSession, user_id: int) -> int:
        """Подсчитать количество предсказаний пользователя за сегодня"""
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)
        stmt = select(func.count(PredictionHistory.id)).where(
            and_(
                PredictionHistory.user_id == user_id,
                PredictionHistory.created_at >= today_start
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0
    
    @staticmethod
    async def delete_by_id(session: AsyncSession, prediction_id: int) -> bool:
        """Удалить запись по ID"""
        stmt = select(PredictionHistory).where(PredictionHistory.id == prediction_id)
        result = await session.execute(stmt)
        prediction = result.scalar_one_or_none()
        
        if prediction:
            await session.delete(prediction)
            await session.commit()
            logger.info(f"Удалена запись истории предсказаний #{prediction_id}")
            return True
        return False
    
    @staticmethod
    async def get_user_statistics(session: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Получить статистику предсказаний пользователя"""
        # Общее количество
        total_stmt = select(func.count(PredictionHistory.id)).where(PredictionHistory.user_id == user_id)
        total_result = await session.execute(total_stmt)
        total = total_result.scalar() or 0
        
        # Количество по типам
        type_stmt = (
            select(PredictionHistory.prediction_type, func.count(PredictionHistory.id))
            .where(PredictionHistory.user_id == user_id)
            .group_by(PredictionHistory.prediction_type)
        )
        type_result = await session.execute(type_stmt)
        type_counts = {ptype.value: count for ptype, count in type_result.all()}
        
        # Последнее предсказание
        last_stmt = (
            select(PredictionHistory)
            .where(PredictionHistory.user_id == user_id)
            .order_by(desc(PredictionHistory.created_at))
            .limit(1)
        )
        last_result = await session.execute(last_stmt)
        last_prediction = last_result.scalar_one_or_none()
        
        return {
            "total": total,
            "by_type": type_counts,
            "last_prediction": last_prediction.to_dict() if last_prediction else None,
            "today_count": await PredictionHistoryService.get_today_predictions_count(session, user_id)
        }
    
    @staticmethod
    async def get_global_statistics(session: AsyncSession) -> Dict[str, Any]:
        """Получить глобальную статистику предсказаний"""
        # Общее количество
        total_stmt = select(func.count(PredictionHistory.id))
        total_result = await session.execute(total_stmt)
        total = total_result.scalar() or 0
        
        # Количество по типам
        type_stmt = (
            select(PredictionHistory.prediction_type, func.count(PredictionHistory.id))
            .group_by(PredictionHistory.prediction_type)
        )
        type_result = await session.execute(type_stmt)
        type_counts = {ptype.value: count for ptype, count in type_result.all()}
        
        # Количество уникальных пользователей
        unique_users_stmt = select(func.count(func.distinct(PredictionHistory.user_id)))
        unique_users_result = await session.execute(unique_users_stmt)
        unique_users = unique_users_result.scalar() or 0
        
        # Самый популярный тип предсказаний
        if type_counts:
            popular_type = max(type_counts.items(), key=lambda x: x[1])
        else:
            popular_type = ("none", 0)
        
        # Количество за сегодня
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)
        today_stmt = select(func.count(PredictionHistory.id)).where(PredictionHistory.created_at >= today_start)
        today_result = await session.execute(today_stmt)
        today_count = today_result.scalar() or 0
        
        return {
            "total": total,
            "unique_users": unique_users,
            "by_type": type_counts,
            "popular_type": popular_type[0],
            "popular_type_count": popular_type[1],
            "today_count": today_count
        }