"""
Сервис для управления настройками пользователя.
"""

import logging
from datetime import datetime, time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from bot.models.user_settings import UserSettings

logger = logging.getLogger(__name__)


class UserSettingsService:
    """Сервис для работы с настройками пользователя."""
    
    @staticmethod
    async def get_or_create(
        session: AsyncSession,
        user_id: int,
        **defaults
    ) -> UserSettings:
        """Получить настройки пользователя или создать новые."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if settings is None:
            settings = UserSettings(user_id=user_id, **defaults)
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
            logger.debug(f"Созданы настройки для пользователя {user_id}")
        else:
            # Обновляем last_active
            settings.last_active = datetime.utcnow()
            await session.commit()
        
        return settings
    
    @staticmethod
    async def update_settings(
        session: AsyncSession,
        user_id: int,
        **kwargs
    ) -> Optional[UserSettings]:
        """Обновить настройки пользователя."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if settings is None:
            return None
        
        # Обновляем только переданные поля
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(settings)
        logger.debug(f"Обновлены настройки для пользователя {user_id}")
        return settings
    
    @staticmethod
    async def get_users_with_daily_notifications(
        session: AsyncSession,
        target_hour: int,
        target_minute: int
    ) -> list[UserSettings]:
        """Получить пользователей, у которых включены ежедневные уведомления на указанное время."""
        stmt = select(UserSettings).where(
            UserSettings.enable_daily_notifications == True,
            UserSettings.notification_time == time(target_hour, target_minute)
        )
        result = await session.execute(stmt)
        users = result.scalars().all()
        return users
    
    @staticmethod
    async def increment_consultation_count(
        session: AsyncSession,
        user_id: int
    ) -> None:
        """Увеличить счётчик консультаций пользователя."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if settings:
            settings.total_consultations += 1
            await session.commit()
    
    @staticmethod
    async def increment_files_count(
        session: AsyncSession,
        user_id: int
    ) -> None:
        """Увеличить счётчик загруженных файлов."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if settings:
            settings.total_files_uploaded += 1
            await session.commit()
    
    @staticmethod
    async def set_ai_mode(
        session: AsyncSession,
        user_id: int,
        enabled: bool
    ) -> Optional[UserSettings]:
        """Включить/выключить режим ИИ."""
        return await UserSettingsService.update_settings(
            session, user_id, ai_mode=enabled
        )
    
    @staticmethod
    async def set_hybrid_mode(
        session: AsyncSession,
        user_id: int,
        enabled: bool
    ) -> Optional[UserSettings]:
        """Включить/выключить гибридный режим."""
        return await UserSettingsService.update_settings(
            session, user_id, hybrid_mode=enabled
        )
    
    @staticmethod
    async def get_ai_mode(
        session: AsyncSession,
        user_id: int
    ) -> bool:
        """Получить состояние режима ИИ."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        if settings:
            return settings.ai_mode
        return False
    
    @staticmethod
    async def get_hybrid_mode(
        session: AsyncSession,
        user_id: int
    ) -> bool:
        """Получить состояние гибридного режима."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        if settings:
            return settings.hybrid_mode
        return False
    
    @staticmethod
    async def get_user_stats(
        session: AsyncSession,
        user_id: int
    ) -> dict:
        """Получить статистику пользователя."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if not settings:
            return {}
        
        return {
            "user_id": settings.user_id,
            "total_consultations": settings.total_consultations,
            "total_files_uploaded": settings.total_files_uploaded,
            "last_active": settings.last_active,
            "favorite_modules": settings.get_favorite_modules_list(),
            "notification_time": settings.notification_time.strftime("%H:%M"),
            "notifications_enabled": settings.enable_daily_notifications,
        }
    
    @staticmethod
    async def can_make_ai_request(
        session: AsyncSession,
        user_id: int,
        is_premium_user: bool
    ) -> tuple[bool, str]:
        """
        Проверить, может ли пользователь сделать запрос к ИИ.
        
        Returns:
            (can_request: bool, reason: str)
        """
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if not settings:
            # Создаём настройки по умолчанию
            settings = await UserSettingsService.get_or_create(session, user_id)
        
        
        # Проверяем сброс дневного счётчика
        today = datetime.utcnow().date()
        last_request_date = settings.last_ai_request_date.date() if settings.last_ai_request_date else None
        
        if last_request_date != today:
            # Сбрасываем счётчик на новый день
            settings.daily_ai_requests = 0
            settings.last_ai_request_date = datetime.utcnow()
            await session.commit()
        
        # Проверяем лимит
        limit = 15 if is_premium_user else 3  # Премиум: 15, Бесплатно: 3      
                if settings.daily_ai_requests >= limit:
            return False, f"⚠️ *Дневной лимит исчерпан*\n\nВы использовали {settings.daily_ai_requests} из {limit} запросов ИИ за сегодня.\n\nЛимит обновится в 00:00 по UTC."
        
        return True, ""
    
    @staticmethod
    async def increment_ai_request_count(
        session: AsyncSession,
        user_id: int
    ) -> None:
        """Увеличить счётчик запросов ИИ."""
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()
        
        if settings:
            # Проверяем сброс дневного счётчика
            today = datetime.utcnow().date()
            last_request_date = settings.last_ai_request_date.date() if settings.last_ai_request_date else None
            
            if last_request_date != today:
                settings.daily_ai_requests = 1
            else:
                settings.daily_ai_requests += 1
            
            settings.last_ai_request_date = datetime.utcnow()
            await session.commit()
