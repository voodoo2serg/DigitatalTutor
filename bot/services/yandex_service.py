"""
DigitalTutor Bot - Yandex Disk Service
Сервис для работы с Яндекс.Диском
"""
import httpx
import logging
from typing import Optional
from datetime import datetime

from bot.config import config

logger = logging.getLogger(__name__)


class YandexDiskService:
    """Сервис для работы с Яндекс.Диском"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://cloud-api.yandex.net/v1/disk"
        self.headers = {"Authorization": f"OAuth {token}"}
    
    def _map_role(self, role: str) -> str:
        """Преобразовать роль в короткое обозначение для папки."""
        role_map = {
            'vkr': 'ВКР',
            'VKR': 'ВКР',
            'ВКР': 'ВКР',
            'aspirant': 'Аспирант',
            'Аспирант': 'Аспирант',
            'vkr_article': 'ВКРСтатья',
            'ВКР + Статья': 'ВКРСтатья',
            'article_guide': 'Статья',
            'Руководство по статье': 'Статья',
            'work_guide': 'Работа',
            'Руководство по работе': 'Работа',
            'other': 'Проект',
            'Другой проект': 'Проект',
        }
        return role_map.get(role, 'Проект')
    
    def _folder_exists(self, path: str) -> bool:
        """Проверить существование папки на Яндекс.Диске."""
        try:
            url = f"{self.base_url}/resources"
            params = {"path": path}
            
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking folder: {e}")
            return False
    
    def _create_folder(self, path: str) -> bool:
        """Создать папку на Яндекс.Диске."""
        try:
            url = f"{self.base_url}/resources"
            params = {"path": path}
            
            with httpx.Client() as client:
                response = client.put(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                return response.status_code in [201, 409]  # 409 = already exists
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return False
    
    def create_student_folder(self, role: str, student_name: str, group_name: str) -> str:
        """Создать папку для студента."""
        role_folder = self._map_role(role)
        student_folder = f"{group_name}_{student_name}" if group_name else student_name
        
        # Создаём структуру: /DigitalTutor/{role}/{student_folder}
        base_path = f"/DigitalTutor/{role_folder}"
        full_path = f"{base_path}/{student_folder}"
        
        if not self._folder_exists(base_path):
            self._create_folder(base_path)
        
        if not self._folder_exists(full_path):
            self._create_folder(full_path)
        
        logger.info(f"Created/accessed folder: {full_path}")
        return full_path
    
    def upload_student_file(self, local_path: str, disk_folder: str, filename: str) -> str:
        """Загрузить файл студента на Яндекс.Диск."""
        try:
            file_path = f"{disk_folder}/{filename}"
            
            # Получаем URL для загрузки
            url = f"{self.base_url}/resources/upload"
            params = {"path": file_path, "overwrite": "true"}
            
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to get upload URL: {response.status_code}")
                
                upload_url = response.json().get("href")
                
                # Загружаем файл
                with open(local_path, 'rb') as f:
                    upload_result = client.put(
                        upload_url,
                        content=f.read(),
                        timeout=60.0
                    )
                
                if upload_result.status_code in [201, 202, 200]:
                    logger.info(f"Uploaded file: {file_path}")
                    return file_path
                else:
                    raise Exception(f"Failed to upload file: {upload_result.status_code}")
                    
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise
    
    def get_public_link(self, disk_path: str) -> Optional[str]:
        """Получить публичную ссылку на файл."""
        try:
            url = f"{self.base_url}/resources"
            params = {"path": disk_path}
            
            with httpx.Client() as client:
                response = client.get(url, headers=self.headers, params=params, timeout=30.0)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("public_url"):
                        return data["public_url"]
                    
                    # Публикуем файл
                    publish_url = f"{self.base_url}/resources/publish"
                    response = client.put(publish_url, headers=self.headers, params=params, timeout=30.0)
                    
                    if response.status_code == 200:
                        response = client.get(url, headers=self.headers, params=params, timeout=30.0)
                        if response.status_code == 200:
                            return response.json().get("public_url")
                            
        except Exception as e:
            logger.error(f"Error getting public link: {e}")
        return None


# Глобальный экземпляр сервиса
yandex_service = YandexDiskService(token=config.YANDEX_DISK_TOKEN)
