"""
Сервис расширенного поиска пользователей для админ-панели.
Поддерживает фильтры по ID, имени, активности, заказам и т.д.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_, desc, distinct, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from bot.models.user_settings import UserSettings
from bot.models.order import Order, OrderStatus
from bot.models.consultation import Consultation
from bot.models.prediction_history import PredictionHistory, PredictionType

log = logging.getLogger(__name__)


class UserSearchService:
    """Сервис расширенного поиска пользователей"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def search_users(
        self,
        query: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        min_consultations: Optional[int] = None,
        min_orders: Optional[int] = None,
        min_predictions: Optional[int] = None,
        has_paid_order: Optional[bool] = None,
        is_active: Optional[bool] = None,  # активен за последние N дней
        active_days: int = 7,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Поиск пользователей с фильтрами
        
        Returns:
            (список пользователей, общее количество)
        """
        # Базовый запрос для пользователей
        stmt = select(UserSettings)
        
        # Применяем фильтры
        if user_id:
            stmt = stmt.where(UserSettings.user_id == user_id)
        
        if query:
            # Поиск по username или first_name
            query_like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    UserSettings.user_id.cast(String).ilike(query_like),
                    text("EXISTS (SELECT 1 FROM orders WHERE orders.user_id = user_settings.user_id AND (orders.username ILIKE :q OR orders.first_name ILIKE :q))")
                )
            )
        
        if username:
            stmt = stmt.where(
                text("EXISTS (SELECT 1 FROM orders WHERE orders.user_id = user_settings.user_id AND orders.username ILIKE :username)")
            )
        
        if first_name:
            stmt = stmt.where(
                text("EXISTS (SELECT 1 FROM orders WHERE orders.user_id = user_settings.user_id AND orders.first_name ILIKE :first_name)")
            )
        
        if min_consultations is not None:
            stmt = stmt.where(
                UserSettings.total_consultations >= min_consultations
            )
        
        if has_paid_order is not None:
            if has_paid_order:
                stmt = stmt.where(
                    text("EXISTS (SELECT 1 FROM orders WHERE orders.user_id = user_settings.user_id AND orders.is_paid = TRUE)")
                )
            else:
                stmt = stmt.where(
                    text("NOT EXISTS (SELECT 1 FROM orders WHERE orders.user_id = user_settings.user_id AND orders.is_paid = TRUE)")
                )
        
        if is_active is not None:
            active_date = datetime.utcnow() - timedelta(days=active_days)
            if is_active:
                stmt = stmt.where(UserSettings.last_active >= active_date)
            else:
                stmt = stmt.where(UserSettings.last_active < active_date)
        
        # Подсчет общего количества
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()
        
        # Получение данных с пагинацией
        stmt = stmt.order_by(desc(UserSettings.last_active)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        users = result.scalars().all()
        
        # Обогащаем данные дополнительной информацией
        enriched_users = []
        for user in users:
            user_data = await self._enrich_user_data(user)
            enriched_users.append(user_data)
        
        return enriched_users, total
    
    async def _enrich_user_data(self, user: UserSettings) -> Dict[str, Any]:
        """Обогащает данные пользователя статистикой"""
        # Статистика заказов
        orders_stmt = select(func.count(Order.id)).where(Order.user_id == user.user_id)
        orders_result = await self.session.execute(orders_stmt)
        total_orders = orders_result.scalar() or 0
        
        # Оплаченные заказы
        paid_orders_stmt = select(func.count(Order.id)).where(
            and_(Order.user_id == user.user_id, Order.is_paid == True)
        )
        paid_orders_result = await self.session.execute(paid_orders_stmt)
        paid_orders = paid_orders_result.scalar() or 0
        
        # Консультации
        consultations_stmt = select(func.count(Consultation.id)).where(Consultation.user_id == user.user_id)
        consultations_result = await self.session.execute(consultations_stmt)
        total_consultations = consultations_result.scalar() or 0
        
        # Предсказания
        predictions_stmt = select(func.count(PredictionHistory.id)).where(PredictionHistory.user_id == user.user_id)
        predictions_result = await self.session.execute(predictions_stmt)
        total_predictions = predictions_result.scalar() or 0
        
        # Последний заказ
        last_order_stmt = select(Order).where(Order.user_id == user.user_id).order_by(desc(Order.created_at)).limit(1)
        last_order_result = await self.session.execute(last_order_stmt)
        last_order = last_order_result.scalar_one_or_none()
        
        # Последняя консультация
        last_consultation_stmt = select(Consultation).where(Consultation.user_id == user.user_id).order_by(desc(Consultation.created_at)).limit(1)
        last_consultation_result = await self.session.execute(last_consultation_stmt)
        last_consultation = last_consultation_result.scalar_one_or_none()
        
        return {
            "user_id": user.user_id,
            "preferred_language": user.preferred_language,
            "last_active": user.last_active.isoformat() if user.last_active else None,
            "total_consultations": total_consultations,
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "total_predictions": total_predictions,
            "ai_mode": user.ai_mode,
            "hybrid_mode": user.hybrid_mode,
            "daily_ai_requests": user.daily_ai_requests,
            "ai_requests_limit": user.ai_requests_limit,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_order": {
                "id": last_order.id,
                "status": last_order.status.value,
                "is_paid": last_order.is_paid,
                "created_at": last_order.created_at.isoformat() if last_order else None
            } if last_order else None,
            "last_consultation": {
                "id": last_consultation.id,
                "created_at": last_consultation.created_at.isoformat() if last_consultation else None
            } if last_consultation else None
        }
    
    async def get_user_detailed_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение детальной статистики по пользователю"""
        # Основная информация
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return {"error": "User not found"}
        
        # Все заказы
        orders_stmt = select(Order).where(Order.user_id == user_id).order_by(desc(Order.created_at))
        orders_result = await self.session.execute(orders_stmt)
        orders = orders_result.scalars().all()
        
        # Все консультации
        consultations_stmt = select(Consultation).where(Consultation.user_id == user_id).order_by(desc(Consultation.created_at))
        consultations_result = await self.session.execute(consultations_stmt)
        consultations = consultations_result.scalars().all()
        
        # Предсказания по типам
        predictions_stmt = select(PredictionHistory).where(PredictionHistory.user_id == user_id).order_by(desc(PredictionHistory.created_at))
        predictions_result = await self.session.execute(predictions_stmt)
        predictions = predictions_result.scalars().all()
        
        # Группировка предсказаний по типам
        prediction_counts = {}
        for pred in predictions:
            pred_type = pred.prediction_type.value
            prediction_counts[pred_type] = prediction_counts.get(pred_type, 0) + 1
        
        return {
            "user": await self._enrich_user_data(user),
            "orders": [
                {
                    "id": order.id,
                    "question": order.question[:100] + "..." if len(order.question) > 100 else order.question,
                    "status": order.status.value,
                    "is_paid": order.is_paid,
                    "created_at": order.created_at.isoformat() if order.created_at else None
                }
                for order in orders[:10]  # Ограничиваем 10 последними
            ],
            "consultations": [
                {
                    "id": consult.id,
                    "question": consult.question[:100] + "..." if len(consult.question) > 100 else consult.question,
                    "created_at": consult.created_at.isoformat() if consult.created_at else None
                }
                for consult in consultations[:10]
            ],
            "predictions_by_type": prediction_counts,
            "total_predictions": len(predictions),
            "recent_activity": {
                "last_order": orders[0].created_at.isoformat() if orders else None,
                "last_consultation": consultations[0].created_at.isoformat() if consultations else None,
                "last_prediction": predictions[0].created_at.isoformat() if predictions else None
            }
        }
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Глобальная статистика по всем пользователям"""
        # Общее количество пользователей
        total_users_stmt = select(func.count(UserSettings.id))
        total_users_result = await self.session.execute(total_users_stmt)
        total_users = total_users_result.scalar() or 0
        
        # Активные пользователи (за последние 7 дней)
        active_date = datetime.utcnow() - timedelta(days=7)
        active_users_stmt = select(func.count(UserSettings.id)).where(UserSettings.last_active >= active_date)
        active_users_result = await self.session.execute(active_users_stmt)
        active_users = active_users_result.scalar() or 0
        
        # Пользователи с оплаченными заказами
        paid_users_stmt = select(func.count(distinct(Order.user_id))).where(Order.is_paid == True)
        paid_users_result = await self.session.execute(paid_users_stmt)
        paid_users = paid_users_result.scalar() or 0
        
        # Новые пользователи за сегодня
        today = datetime.utcnow().date()
        new_users_today_stmt = select(func.count(UserSettings.id)).where(
            func.date(UserSettings.created_at) == today
        )
        new_users_today_result = await self.session.execute(new_users_today_stmt)
        new_users_today = new_users_today_result.scalar() or 0
        
        # Распределение по языкам
        languages_stmt = select(
            UserSettings.preferred_language,
            func.count(UserSettings.id)
        ).group_by(UserSettings.preferred_language)
        languages_result = await self.session.execute(languages_stmt)
        languages = dict(languages_result.all())
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "paid_users": paid_users,
            "new_users_today": new_users_today,
            "activity_rate": round((active_users / total_users * 100), 2) if total_users > 0 else 0,
            "conversion_rate": round((paid_users / total_users * 100), 2) if total_users > 0 else 0,
            "languages": languages
        }


# Утилитарные функции для работы с поиском
async def search_users_by_criteria(session: AsyncSession, **kwargs) -> Tuple[List[Dict[str, Any]], int]:
    """Упрощённый интерфейс для поиска пользователей"""
    service = UserSearchService(session)
    return await service.search_users(**kwargs)


async def get_user_full_profile(session: AsyncSession, user_id: int) -> Dict[str, Any]:
    """Получение полного профиля пользователя"""
    service = UserSearchService(session)

    return await service.get_user_detailed_stats(user_id)
