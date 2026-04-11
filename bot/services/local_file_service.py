"""
Local File Storage Service for DigitalTutor
Основное хранение файлов на сервере, Яндекс.Диск как опция
"""
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

# Базовая папка для файлов
BASE_STORAGE_PATH = Path("/app/data/student_files")

class LocalFileService:
    """Сервис для локального хранения файлов студентов"""
    
    def __init__(self):
        self.base_path = BASE_STORAGE_PATH
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создать необходимые директории"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "works").mkdir(exist_ok=True)
        (self.base_path / "temp").mkdir(exist_ok=True)
        logger.info(f"Local storage initialized at {self.base_path}")
    
    def save_work_file(self, file_data: bytes, original_filename: str, student_id: str, work_id: str) -> Tuple[str, str]:
        """
        Сохранить файл работы локально
        
        Returns:
            (local_path, file_uuid)
        """
        file_uuid = str(uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Безопасное имя файла
        safe_name = "".join(c for c in original_filename if c.isalnum() or c in '._-').strip()
        if not safe_name:
            safe_name = "file"
        
        # Структура: /works/{student_id}/{work_id}/{timestamp}_{uuid}_{filename}
        student_dir = self.base_path / "works" / student_id
        student_dir.mkdir(parents=True, exist_ok=True)
        
        local_filename = f"{timestamp}_{file_uuid}_{safe_name}"
        local_path = student_dir / local_filename
        
        # Сохраняем файл
        with open(local_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"File saved locally: {local_path}")
        return str(local_path), file_uuid
    
    def get_file(self, local_path: str) -> Optional[bytes]:
        """Получить файл по локальному пути"""
        try:
            full_path = self.base_path / local_path if not os.path.isabs(local_path) else Path(local_path)
            if full_path.exists():
                with open(full_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            logger.error(f"Error reading file {local_path}: {e}")
            return None
    
    def delete_file(self, local_path: str) -> bool:
        """Удалить файл (только для админа)"""
        try:
            full_path = Path(local_path) if os.path.isabs(local_path) else self.base_path / local_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"File deleted: {full_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {local_path}: {e}")
            return False
    
    def get_file_info(self, local_path: str) -> Optional[dict]:
        """Получить информацию о файле"""
        try:
            full_path = Path(local_path) if os.path.isabs(local_path) else self.base_path / local_path
            if full_path.exists():
                stat = full_path.stat()
                return {
                    "path": str(full_path),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime),
                    "modified": datetime.fromtimestamp(stat.mtime)
                }
            return None
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def list_student_files(self, student_id: str) -> list:
        """Получить список файлов студента"""
        student_dir = self.base_path / "works" / student_id
        if not student_dir.exists():
            return []
        
        files = []
        for file_path in student_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                })
        return sorted(files, key=lambda x: x["modified"], reverse=True)


# Глобальный экземпляр
local_file_service = LocalFileService()
