"""
Reviews API Routes
Управление проверками и AI-анализом
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import structlog

from src.database import get_db
from src.models.schemas import (
    ReviewCreate, ReviewResponse, AIAnalysisRequest, AIAnalysisResponse
)

router = APIRouter()
logger = structlog.get_logger()


@router.post("/", response_model=ReviewResponse, status_code=201)
async def create_review(
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать проверку работы

    После создания автоматически обновляется статус работы.
    """
    # Проверяем существование работы
    sub_query = select(Submission).where(Submission.id == review_data.submission_id)
    sub_result = await db.execute(sub_query)
    submission = sub_result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    review = Review(
        **review_data.model_dump(),
        created_by_telegram_id=0  # TODO: Из контекста
    )

    db.add(review)

    # Обновляем статус работы
    submission.status = review_data.status.value
    submission.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(review)

    logger.info(
        "Review created",
        review_id=str(review.id),
        submission_id=str(review_data.submission_id),
        new_status=review_data.status.value
    )

    return review


@router.get("/submission/{submission_id}", response_model=List[ReviewResponse])
async def list_reviews(
    submission_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить все проверки для работы
    """
    query = select(Review).where(Review.submission_id == submission_id)
    query = query.order_by(Review.created_at.desc())

    result = await db.execute(query)
    reviews = result.scalars().all()

    return reviews


@router.post("/ai-analysis", response_model=AIAnalysisResponse)
async def analyze_with_ai(
    request: AIAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Запустить AI-анализ файла

    Анализ включает:
    - Определение процента AI-генерированного текста
    - Оценку качества работы
    - Выявление типичных проблем
    - Рекомендации по улучшению
    """
    # Получаем файл
    query = select(File).where(File.id == request.file_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # TODO: Реальный AI-анализ
    # if settings.AI_API_KEY:
    #     analysis = await perform_ai_analysis(file, request.analysis_type)

    # Заглушка для демонстрации
    analysis = AIAnalysisResponse(
        file_id=request.file_id,
        ai_generated_probability=0.35,
        quality_score=7.5,
        issues=[
            {"type": "structure", "description": "Отсутствует введение", "severity": "medium"},
            {"type": "citation", "description": "Мало источников (3 из 5 минимум)", "severity": "high"},
        ],
        recommendations=[
            "Добавить введение с постановкой задачи",
            "Включить минимум 2 дополнительных источника",
            "Усилить аргументацию во второй главе"
        ],
        summary="Работа имеет хорошую структуру, но требует доработки введения и списка источников. Рекомендуется к защите после устранения замечаний."
    )

    logger.info(
        "AI analysis completed",
        file_id=request.file_id,
        analysis_type=request.analysis_type
    )

    return analysis


@router.post("/{review_id}/attach-signature")
async def attach_signature(
    review_id: str,
    signature_image: str = None,  # Base64 image
    db: AsyncSession = Depends(get_db)
):
    """
    Прикрепить электронную подпись к проверке

    Используется для официальных отзывов и рецензий.
    """
    query = select(Review).where(Review.id == review_id)
    result = await db.execute(query)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.signature_attached = True
    review.signed_at = datetime.utcnow()

    await db.flush()

    logger.info("Signature attached", review_id=str(review_id))

    return {"status": "ok", "signed_at": review.signed_at.isoformat()}


# Модели
from sqlalchemy import Column, String, DateTime, Text, Integer, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base
from datetime import datetime


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True)
    submission_id = Column(UUID(as_uuid=True), nullable=False)
    file_id = Column(UUID(as_uuid=True))
    review_type = Column(String(50), nullable=False)
    stage = Column(String(50))
    status = Column(String(50), nullable=False)
    comment = Column(Text)
    grade = Column(Integer)
    signature_attached = Column(Boolean, default=False)
    signed_at = Column(DateTime)
    ai_analysis = Column(JSONB)
    ai_model = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_telegram_id = Column(BigInteger, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    status = Column(String(50))
    updated_at = Column(DateTime)


class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True)
    storage_path = Column(Text)
    original_filename = Column(Text)
    mime_type = Column(String(255))
