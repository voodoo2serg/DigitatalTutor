"""
Конфигурация приложения
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://studobot:studobot@localhost:5432/studobot"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "student-files"
    MINIO_USE_SSL: bool = False

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TEACHER_TELEGRAM_ID: Optional[int] = None

    # AI
    AI_API_KEY: Optional[str] = None
    AI_API_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4"

    # Security
    JWT_SECRET: str = "change_this_to_random_string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # App
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
