"""
Students API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional
import structlog

from src.database import get_db
from src.models.schemas import (
    StudentCreate, StudentUpdate, StudentResponse, StudentWithSubmissions,
    StudentRole
)

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=List[StudentResponse])
async def list_students(
    role: Optional[StudentRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список студентов с фильтрацией

    - **role**: фильтр по роли (student, monitor, phd)
    - **is_active**: только активные/неактивные
    - **search**: поиск по имени, группе, заметкам
    """
    query = select(Student).where(Student.is_active == True if is_active is None else Student.is_active == is_active)

    if role:
        query = query.where(Student.role == role)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Student.display_name.ilike(search_term),
                Student.group_name.ilike(search_term),
                Student.notes.ilike(search_term)
            )
        )

    query = query.order_by(Student.last_interaction_at.desc().nullslast())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    students = result.scalars().all()

    return students


@router.get("/{student_id}", response_model=StudentWithSubmissions)
async def get_student(
    student_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить студента по ID с его активными работами
    """
    query = select(Student).where(Student.id == student_id)
    result = await db.execute(query)
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Получаем активные работы
    subs_query = select(Submission).where(
        Submission.student_id == student_id,
        Submission.status.notin_(['approved', 'rejected'])
    ).order_by(Submission.actual_deadline)

    subs_result = await db.execute(subs_query)
    active_submissions = subs_result.scalars().all()

    # Считаем общее количество работ
    count_query = select(func.count(Submission.id)).where(Submission.student_id == student_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return StudentWithSubmissions(
        **student.__dict__,
        active_submissions=active_submissions,
        total_submissions=total
    )


@router.get("/telegram/{telegram_id}", response_model=StudentResponse)
async def get_student_by_telegram(
    telegram_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить студента по Telegram ID
    """
    query = select(Student).where(Student.telegram_id == telegram_id)
    result = await db.execute(query)
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return student


@router.post("/", response_model=StudentResponse, status_code=201)
async def create_student(
    student_data: StudentCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать нового студента

    Обычно студенты создаются автоматически при первом взаимодействии с ботом.
    """
    # Проверяем, не существует ли уже
    existing = await db.execute(
        select(Student).where(Student.telegram_id == student_data.telegram_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Student with this Telegram ID already exists")

    student = Student(**student_data.model_dump())
    db.add(student)
    await db.flush()
    await db.refresh(student)

    logger.info("Student created", student_id=str(student.id), telegram_id=student.telegram_id)

    return student


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    student_data: StudentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить данные студента
    """
    query = select(Student).where(Student.id == student_id)
    result = await db.execute(query)
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_data = student_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    await db.flush()
    await db.refresh(student)

    logger.info("Student updated", student_id=str(student.id))

    return student


@router.delete("/{student_id}", status_code=204)
async def deactivate_student(
    student_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Деактивировать студента (мягкое удаление)

    Студент остаётся в базе для сохранения истории, но не участвует в активных работах.
    """
    query = select(Student).where(Student.id == student_id)
    result = await db.execute(query)
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.is_active = False
    await db.flush()

    logger.info("Student deactivated", student_id=str(student.id))


# Временный импорт моделей (в реальном проекте - отдельный файл models.py)
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, BigInteger, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base
import enum

class Student(Base):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=True), primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    telegram_username = Column(String(255))
    display_name = Column(Text, nullable=False)
    group_name = Column(Text)
    notes = Column(Text)
    role = Column(String(20), default='student')
    is_active = Column(Boolean, default=True)
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    last_interaction_at = Column(DateTime)


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    student_id = Column(UUID(as_uuid=True), nullable=False)
    assignment_type_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(Text)
    description = Column(Text)
    current_stage = Column(String(50), nullable=False)
    status = Column(String(50), default='pending')
    base_deadline = Column(DateTime)
    extended_deadline = Column(DateTime)
    actual_deadline = Column(DateTime)
    artifact_url = Column(Text)
    artifact_type = Column(String(20))
    artifact_metadata = Column(JSONB, default={})
    grade = Column(Integer)
    grade_date = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    completed_at = Column(DateTime)
