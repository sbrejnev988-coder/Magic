"""
Сервис для работы с заказами консультаций.
"""

import logging
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)


class OrderService:
    """Сервис управления заказами"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(
        self,
        user_id: int,
        question: str,
        birth_date: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> Order:
        """Создать новый заказ"""
        order = Order(
            user_id=user_id,
            username=username,
            first_name=first_name,
            question=question,
            birth_date=birth_date,
            status=OrderStatus.NEW,
        )
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        logger.info(f"Создан заказ #{order.id} для пользователя {user_id}")
        return order

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Получить заказ по ID"""
        stmt = select(Order).where(Order.id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_orders_by_user(self, user_id: int, limit: int = 10) -> List[Order]:
        """Получить заказы пользователя"""
        stmt = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_orders_by_status(self, status: OrderStatus, limit: int = 50) -> List[Order]:
        """Получить заказы по статусу"""
        stmt = select(Order).where(Order.status == status).order_by(Order.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_orders(self, limit: int = 50) -> List[Order]:
        """Получить все заказы (последние)"""
        stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unpaid_orders(self, limit: int = 50) -> List[Order]:
        """Получить неоплаченные заказы"""
        stmt = select(Order).where(Order.is_paid == False).order_by(Order.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, order_id: int, status: OrderStatus) -> Optional[Order]:
        """Обновить статус заказа"""
        stmt = update(Order).where(Order.id == order_id).values(status=status)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_order_by_id(order_id)

    async def mark_as_paid(
        self,
        order_id: int,
        screenshot_file_id: Optional[str] = None,
        admin_notes: Optional[str] = None
    ) -> Optional[Order]:
        """Пометить заказ как оплаченный"""
        update_data = {
            "is_paid": True,
        }
        if screenshot_file_id:
            update_data["payment_screenshot"] = screenshot_file_id
        if admin_notes:
            update_data["admin_notes"] = admin_notes
        
        stmt = update(Order).where(Order.id == order_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_order_by_id(order_id)

    async def add_payment_screenshot(self, order_id: int, screenshot_file_id: str) -> Optional[Order]:
        """Добавить скриншот оплаты к заказу"""
        stmt = update(Order).where(Order.id == order_id).values(payment_screenshot=screenshot_file_id)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_order_by_id(order_id)

    async def add_admin_notes(self, order_id: int, notes: str) -> Optional[Order]:
        """Добавить заметки администратора"""
        stmt = update(Order).where(Order.id == order_id).values(admin_notes=notes)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_order_by_id(order_id)

    async def count_orders_by_status(self, status: OrderStatus) -> int:
        """Подсчитать количество заказов по статусу"""
        stmt = select(Order).where(Order.status == status)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def has_paid_order(self, user_id: int) -> bool:
        """Проверить, есть ли у пользователя оплаченный заказ"""
        stmt = select(Order).where(
            Order.user_id == user_id,
            Order.is_paid == True
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None