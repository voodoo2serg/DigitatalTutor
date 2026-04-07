"""
MinIO Service for DigitalTutor Bot - File operations
ИСПРАВЛЕНО: Сначала ищем файлы локально, потом в MinIO
"""
import logging
import os
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

# MinIO configuration
MINIO_EXTERNAL_ENDPOINT = os.getenv("MINIO_EXTERNAL_ENDPOINT", "213.171.9.30:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "student-works")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Local storage path - должен совпадать с local_file_service
LOCAL_STORAGE_PATH = Path("/app/data/student_files")


def get_file_download_url(filename: str, expiry: int = 3600) -> str:
    """Generate direct download URL for file"""
    try:
        protocol = "https" if MINIO_SECURE else "http"
        url = f"{protocol}://{MINIO_EXTERNAL_ENDPOINT}/{MINIO_BUCKET}/{filename}"
        return url
    except Exception as e:
        logger.error(f"Error generating download URL for {filename}: {e}")
        return None


def find_local_file(filename: str) -> str:
    """
    Искать файл локально в разных местах
    Returns: полный путь к файлу или None
    """
    # Варианты где может быть файл
    possible_paths = [
        LOCAL_STORAGE_PATH / filename,
        LOCAL_STORAGE_PATH / "works" / filename,
        Path(f"/tmp/{filename}"),
    ]
    
    # Ищем по всей структуре works/
    works_dir = LOCAL_STORAGE_PATH / "works"
    if works_dir.exists():
        for path in works_dir.rglob(filename):
            if path.is_file():
                logger.info(f"Local file found via rglob: {path}")
                return str(path)
    
    # Проверяем стандартные пути
    for path in possible_paths:
        if path.exists():
            logger.info(f"Local file found: {path}")
            return str(path)
    
    # Если имя файла содержит путь - ищем по частям
    if "/" in filename or "\\" in filename:
        # Пробуем найти только по имени файла
        basename = os.path.basename(filename)
        if works_dir.exists():
            for path in works_dir.rglob(basename):
                if path.is_file():
                    logger.info(f"Local file found by basename: {path}")
                    return str(path)
    
    return None


async def download_file_to_temp(filename: str) -> str:
    """
    Download file to temporary location
    ИСПРАВЛЕНО: Сначала ищем локально, потом пытаемся скачать из MinIO
    
    Returns:
        Path to file or None if error
    """
    # СНАЧАЛА ищем локально
    local_path = find_local_file(filename)
    if local_path:
        return local_path
    
    # Если не нашли локально - пробуем скачать из MinIO (для старых файлов)
    try:
        url = get_file_download_url(filename)
        if not url:
            return None
        
        # Извлекаем basename для сохранения
        basename = os.path.basename(filename)
        temp_path = f"/tmp/{basename}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            
            with open(temp_path, "wb") as f:
                f.write(response.content)
        
        logger.info(f"File downloaded from MinIO: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Error downloading file {filename} from MinIO: {e}")
        return None
