"""
Сервис для управления файлами клиентов.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional, Tuple
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.models.consultation_file import ConsultationFile

logger = logging.getLogger(__name__)


class ClientFilesService:
    """Управление файлами клиентов."""
    
    # Базовый путь для файлов клиентов
    BASE_CLIENTS_PATH = Path("C:/Users/Kekl/.openclaw/workspace/uploads/clients")
    
    @classmethod
    def get_client_path(cls, user_id: int) -> Path:
        """Получить путь к папке клиента."""
        return cls.BASE_CLIENTS_PATH / str(user_id)
    
    @classmethod
    def get_documents_path(cls, user_id: int) -> Path:
        """Путь к документам клиента."""
        return cls.get_client_path(user_id) / "documents"
    
    @classmethod
    def get_images_path(cls, user_id: int) -> Path:
        """Путь к изображениям клиента."""
        return cls.get_client_path(user_id) / "images"
    
    @classmethod
    def get_audio_path(cls, user_id: int) -> Path:
        """Путь к аудиофайлам клиента."""
        return cls.get_client_path(user_id) / "audio"
    
    @classmethod
    def ensure_client_directories(cls, user_id: int):
        """Создать папки клиента, если их нет."""
        paths = [
            cls.get_client_path(user_id),
            cls.get_documents_path(user_id),
            cls.get_images_path(user_id),
            cls.get_audio_path(user_id)
        ]
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Созданы папки для клиента {user_id}")
    
    @classmethod
    def save_uploaded_file(
        cls, 
        user_id: int, 
        file_path: str, 
        original_name: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Сохранить загруженный файл в папку клиента.
        
        Возвращает: (новый_путь, тип_файла) или (None, None) при ошибке.
        """
        try:
            cls.ensure_client_directories(user_id)
            
            # Определяем тип файла по расширению
            ext = Path(original_name).suffix.lower()
            if ext in ['.txt', '.doc', '.docx', '.pdf', '.rtf']:
                file_type = "document"
                dest_dir = cls.get_documents_path(user_id)
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                file_type = "image"
                dest_dir = cls.get_images_path(user_id)
            elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
                file_type = "audio"
                dest_dir = cls.get_audio_path(user_id)
            else:
                file_type = "document"
                dest_dir = cls.get_documents_path(user_id)
            
            # Генерируем уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = Path(original_name).stem.replace(' ', '_')
            new_filename = f"{timestamp}_{safe_name}{ext}"
            dest_path = dest_dir / new_filename
            
            # Копируем файл
            shutil.copy2(file_path, dest_path)
            logger.info(f"Файл сохранён: {dest_path}")
            
            return str(dest_path), file_type
            
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            return None, None
    
    @staticmethod
    async def attach_file_to_consultation(
        session: AsyncSession,
        consultation_id: int,
        user_id: int,
        file_path: str,
        original_name: str,
        file_type: str
    ) -> ConsultationFile:
        """Прикрепить файл к консультации в БД."""
        file_record = ConsultationFile(
            consultation_id=consultation_id,
            user_id=user_id,
            file_path=file_path,
            file_name=original_name,
            file_type=file_type,
            uploaded_at=datetime.utcnow()
        )
        session.add(file_record)
        await session.commit()
        await session.refresh(file_record)
        logger.debug(f"Файл прикреплён к консультации {consultation_id}")
        return file_record
    
    @staticmethod
    async def get_files_for_consultation(
        session: AsyncSession,
        consultation_id: int,
        user_id: Optional[int] = None
    ) -> List[ConsultationFile]:
        """Получить все файлы консультации."""
        stmt = select(ConsultationFile).where(
            ConsultationFile.consultation_id == consultation_id
        )
        if user_id is not None:
            stmt = stmt.where(ConsultationFile.user_id == user_id)
        
        result = await session.execute(stmt)
        files = result.scalars().all()
        return files
    
    @staticmethod
    async def delete_file(
        session: AsyncSession,
        file_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """Удалить файл (только свой)."""
        stmt = select(ConsultationFile).where(ConsultationFile.id == file_id)
        if user_id is not None:
            stmt = stmt.where(ConsultationFile.user_id == user_id)
        
        result = await session.execute(stmt)
        file_record = result.scalar_one_or_none()
        
        if file_record is None:
            return False
        
        # Удаляем физический файл
        try:
            if os.path.exists(file_record.file_path):
                os.remove(file_record.file_path)
        except Exception as e:
            logger.warning(f"Не удалось удалить физический файл: {e}")
        
        # Удаляем запись из БД
        await session.delete(file_record)
        await session.commit()
        return True
    
    @classmethod
    async def process_uploaded_file(
        cls,
        session: AsyncSession,
        user_id: int,
        consultation_id: int,
        temp_file_path: str,
        original_filename: str
    ) -> Optional[ConsultationFile]:
        """Полный процесс обработки загруженного файла."""
        # Сохраняем файл в папку клиента
        saved_path, file_type = cls.save_uploaded_file(
            user_id, temp_file_path, original_filename
        )
        
        if not saved_path:
            return None
        
        # Прикрепляем к консультации в БД
        file_record = await cls.attach_file_to_consultation(
            session=session,
            consultation_id=consultation_id,
            user_id=user_id,
            file_path=saved_path,
            original_name=original_filename,
            file_type=file_type
        )
        
        return file_record