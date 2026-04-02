"""
DigitalTutor Bot - Yandex Disk Service
Сервис для работы с Яндекс.Диском
"""
import httpx
import logging
from typing import Optional
from datetime import datetime

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
            logger.error(f"Error checking folder existence: {e}")
            return False
    
    def create_student_folder(self, fio: str, role: str, year: int = None) -> str:
        """
        Создать папку студента. Формат: ФамилияРольГод
        При конфликте добавляет _N к имени.
        """
        if year is None:
            year = datetime.now().year
            
        surname = fio.split()[0] if fio else "Unknown"
        role_short = self._map_role(role)
        base_name = f"{surname}{role_short}{year}"
        
        counter = 1
        folder_path = f"app:/DigitalTutor/{base_name}"
        
        # Проверяем существование папки
        while self._folder_exists(folder_path):
            counter += 1
            folder_path = f"app:/DigitalTutor/{base_name}_{counter}"
        
        try:
            url = f"{self.base_url}/resources"
            params = {"path": folder_path}
            
            with httpx.Client() as client:
                response = client.put(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code in [201, 202]:
                    logger.info(f"Created folder: {folder_path}")
                    return folder_path
                else:
                    logger.error(f"Failed to create folder: {response.status_code} - {response.text}")
                    raise Exception(f"Failed to create folder: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            raise
    
    async def upload_student_file(self, file_data: bytes, filename: str,
                                   student_folder: str, work_id: str = None) -> str:
        """
        Загрузить файл работы на Яндекс.Диск.
        """
        # Очищаем имя файла от недопустимых символов
        safe_filename = "".join(c for c in filename if c.isalnum() or c in '._- ')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if work_id:
            file_path = f"{student_folder}/work_{work_id}_{timestamp}_{safe_filename}"
        else:
            file_path = f"{student_folder}/{timestamp}_{safe_filename}"
        
        try:
            url = f"{self.base_url}/resources/upload"
            params = {"path": file_path, "overwrite": "false"}
            
            async with httpx.AsyncClient() as client:
                upload_response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                
                if upload_response.status_code != 200:
                    raise Exception(f"Failed to get upload URL: {upload_response.status_code}")
                
                upload_data = upload_response.json()
                upload_url = upload_data.get("href")
                
                if not upload_url:
                    raise Exception("No upload URL in response")
                
                upload_result = await client.put(
                    upload_url,
                    content=file_data,
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
