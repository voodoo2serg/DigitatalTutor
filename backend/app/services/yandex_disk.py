"""
Yandex Disk Service for DigitalTutor
Сервис для работы с Яндекс.Диском
"""

import httpx
from typing import Optional, List, Dict, Any
import logging

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
            'student': 'ВКР',
            'aspirant': 'Аспирант',
            'Аспирант': 'Аспирант',
            'vkr_article': 'ВКРСтатья',
            'article_guide': 'Статья',
            'Статья': 'Статья',
            'work_guide': 'Работа',
            'other': 'Проект',
            'Проект': 'Проект'
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
    
    def create_student_folder(self, fio: str, role: str, year: int) -> str:
        """
        Создать папку студента. Формат: ФамилияРольГод
        При конфликте добавляет _N к имени.
        """
        surname = fio.split()[0] if fio else "Unknown"
        role_short = self._map_role(role)
        base_name = f"{surname}{role_short}{year}"
        
        counter = 1
        folder_path = f"/DigitalTutor/{base_name}"
        
        while self._folder_exists(folder_path):
            counter += 1
            folder_path = f"/DigitalTutor/{base_name}_{counter}"
        
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
                    raise Exception(f"Failed to create folder: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            raise
    
    def upload_student_file(self, file_data: bytes, filename: str,
                           student_folder: str, work_id: str) -> str:
        """
        Загрузить файл работы на Яндекс.Диск.
        """
        file_path = f"{student_folder}/work_{work_id}_{filename}"
        
        try:
            url = f"{self.base_url}/resources/upload"
            params = {"path": file_path, "overwrite": "false"}
            
            with httpx.Client() as client:
                upload_response = client.get(
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
                
                upload_result = client.put(
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
    
    def upload_communication(self, messages: List[Dict[str, Any]], work_id: str,
                            student_folder: str) -> str:
        """
        Сохранить переписку в txt файл.
        """
        content_lines = ["=== ИСТОРИЯ ПЕРЕПИСКИ ===", ""]
        
        for msg in messages:
            timestamp = msg.get('created_at', 'Unknown time')
            sender = "СТУДЕНТ" if msg.get('from_student') else "РУКОВОДИТЕЛЬ"
            text = msg.get('message', '')
            content_lines.append(f"[{timestamp}] [{sender}]: {text}")
        
        content_lines.extend(["", "=== КОНЕЦ ==="])
        content = "\n".join(content_lines)
        
        filename = f"communication_history_{work_id}.txt"
        file_path = f"{student_folder}/{filename}"
        
        try:
            url = f"{self.base_url}/resources/upload"
            params = {"path": file_path, "overwrite": "true"}
            
            with httpx.Client() as client:
                upload_response = client.get(
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
                
                upload_result = client.put(
                    upload_url,
                    content=content.encode('utf-8'),
                    timeout=30.0
                )
                
                if upload_result.status_code in [201, 202, 200]:
                    logger.info(f"Uploaded communication history: {file_path}")
                    return file_path
                else:
                    raise Exception(f"Failed to upload communication: {upload_result.status_code}")
                    
        except Exception as e:
            logger.error(f"Error uploading communication: {e}")
            raise
    
    def list_my_files(self) -> List[Dict[str, Any]]:
        """
        Получить список файлов из папки /DigitalTutor/Мое/
        """
        try:
            url = f"{self.base_url}/resources"
            params = {
                "path": "/DigitalTutor/Мое/",
                "limit": 100
            }
            
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to list files: {response.status_code}")
                    return []
                
                data = response.json()
                items = data.get("_embedded", {}).get("items", [])
                
                files = []
                for item in items:
                    if item.get("type") == "file":
                        files.append({
                            "name": item.get("name"),
                            "path": item.get("path"),
                            "size": item.get("size"),
                            "modified": item.get("modified"),
                            "mime_type": item.get("mime_type")
                        })
                
                return files
                
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get_download_link(self, path: str) -> str:
        """
        Получить временную ссылку на скачивание файла.
        """
        try:
            url = f"{self.base_url}/resources/download"
            params = {"path": path}
            
            with httpx.Client() as client:
                response = client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Failed to get download link: {response.status_code}")
                
                data = response.json()
                download_url = data.get("href")
                
                if not download_url:
                    raise Exception("No download URL in response")
                
                return download_url
                
        except Exception as e:
            logger.error(f"Error getting download link: {e}")
            raise
    
    async def send_file_to_student(self, file_path: str, telegram_id: int,
                                    bot_token: str, caption: str = "") -> bool:
        """
        Отправить файл студенту через Telegram Bot API.
        """
        try:
            download_url = self.get_download_link(file_path)
            telegram_url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            
            async with httpx.AsyncClient() as client:
                file_response = await client.get(download_url, timeout=60.0)
                
                if file_response.status_code != 200:
                    logger.error(f"Failed to download file from Yandex: {file_response.status_code}")
                    return False
                
                file_data = file_response.content
                
                filename = file_path.split("/")[-1]
                files = {"document": (filename, file_data)}
                data = {"chat_id": telegram_id, "caption": caption}
                
                response = await client.post(
                    telegram_url,
                    data=data,
                    files=files,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    logger.info(f"File sent to student {telegram_id}")
                    return True
                else:
                    logger.error(f"Failed to send file to Telegram: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending file to student: {e}")
            return False

    def get_public_link(self, disk_path: str) -> Optional[str]:
        """Получить публичную ссылку на файл. Если файл не опубликован — публикует его."""
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

