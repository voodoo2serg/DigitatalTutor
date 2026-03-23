from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "DigitalTutor"
    DEBUG: bool = False
    
    # Database
    POSTGRES_USER: str = "teacher"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "teaching"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: str = "5432"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "teacher"
    MINIO_SECRET_KEY: str = "changeme"
    MINIO_BUCKET: str = "student-works"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TEACHER_TELEGRAM_ID: str = ""
    
    # AI
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:4b"
    OPENAI_API_KEY: str = ""
    
    # Redis
    REDIS_URL: str = "redis://redis:6379"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
