"""
DigitalTutor Bot - MinIO Service (Fallback)
Заглушка для обратной совместимости.
Использует LocalFileService и YandexDiskService.

FIX: BUG-008 - исправлено скачивание файлов
"""
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from bot.services.local_file_service import local_file_service
from bot.services.yandex_service import yandex_service

logger = logging.getLogger(__name__)


async def get_file_download_url(filename: str, use_yandex: bool = True) -> Optional[str]:
    """
    Получить URL для скачивания файла.
    
    Args:
        filename: Имя файла или путь
        use_yandex: Использовать Яндекс.Диск если доступен
    
    Returns:
        URL для скачивания или None
    """
    try:
        # Пробуем получить публичную ссылку из Яндекс.Диска
        if use_yandex and yandex_service.token:
            # Предполагаем что файл уже на Яндекс.Диске
            public_url = await yandex_service.get_public_link(filename)
            if public_url:
                return public_url
        
        # Если не получилось - возвращаем None (файл будет отправлен напрямую)
        return None
    
    except Exception as e:
        logger.error(f"Error getting download URL for {filename}: {e}")
        return None


async def download_file_to_temp(file_path: str) -> Optional[str]:
    """
    Скачать файл во временную директорию.
    
    Args:
        file_path: Путь к файлу (локальный или на Яндекс.Диске)
    
    Returns:
        Путь к временному файлу или None
    """
    try:
        # Проверяем если это локальный файл
        if os.path.exists(file_path):
            # Копируем во временную директорию
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, os.path.basename(file_path))
            
            with open(file_path, 'rb') as src:
                with open(temp_path, 'wb') as dst:
                    dst.write(src.read())
            
            logger.info(f"File copied to temp: {temp_path}")
            return temp_path
        
        # Пробуем получить из локального сервиса
        file_data = local_file_service.get_file(file_path)
        if file_data:
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, os.path.basename(file_path))
            
            with open(temp_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"File retrieved from local storage: {temp_path}")
            return temp_path
        
        logger.warning(f"File not found: {file_path}")
        return None
    
    except Exception as e:
        logger.error(f"Error downloading file {file_path}: {e}")
        return None
