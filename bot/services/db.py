"""
DigitalTutor Bot - Database Service
Сервис для работы с базой данных

FIX: DT-REPAIR-001 - SQLAlchemy MissingGreenlet
Используем @asynccontextmanager для правильной работы с async сессиями

FIX: 2026-04-12 - Увеличен пул соединений для предотвращения QueuePool limit
"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
import os

# Получаем URL базы данных
database_url = os.getenv("DATABASE_URL", "")
if "postgresql://" in database_url and "asyncpg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    database_url,
    echo=False,
    future=True,
    pool_size=20,           # Увеличено с 5 до 20
    max_overflow=30,        # Увеличено с 10 до 30
    pool_timeout=60,        # Таймаут ожидания соединения
    pool_recycle=3600,      # Пересоздание соединений каждый час
    pool_pre_ping=True      # Проверка соединения перед использованием
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


@asynccontextmanager
async def get_async_session():
    """
    Асинхронный контекстный менеджер для сессий БД.
    
    FIX: Используем @asynccontextmanager вместо async generator
    для предотвращения MissingGreenlet ошибок.
    
    Usage:
        async with get_async_session() as session:
            result = await session.execute(query)
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


class AsyncSessionContext:
    """
    Класс-обертка для сессий БД.
    
    DEPRECATED: Используйте get_async_session() с @asynccontextmanager
    """
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = AsyncSessionLocal()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()
