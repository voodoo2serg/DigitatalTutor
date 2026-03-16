"""
Submissions API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import joinedload
from typing import List, Optional
from datetime import date, timedelta
import structlog

from src.database import get_db
from src.models.schemas import (
    SubmissionCreate, SubmissionUpdate, SubmissionResponse,
    SubmissionWithDetails, SubmissionStatus, AssignmentType,
    WorkloadStats, DeadlineStatus
)

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=List[SubmissionResponse])
async def list_submissions(
    student_id: Optional[str] = None,
    assignment_type: Optional[AssignmentType] = None,
    status: Optional[SubmissionStatus] = None,
    stage: Optional[str] = None,
    deadline_from: Optional[date] = None,
    deadline_to: Optional[date] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список работ с фильтрацией

    - **student_id**: фильтр по студенту
    - **assignment_type**: тип задания
    - **status**: статус работы
    - **stage**: текущий этап
    - **deadline_from/to**: диапазон дедлайнов
    """
    query = select(Submission)

    if student_id:
        query = query.where(Submission.student_id == student_id)
    if status:
        query = query.where(Submission.status == status.value)
    if stage:
        query = query.where(Submission.current_stage == stage)

    if deadline_from:
        query = query.where(Submission.actual_deadline >= deadline_from)
    if deadline_to:
        query = query.where(Submission.actual_deadline <= deadline_to)

    # Сортировка: сначала просроченные, потом по дедлайну
    query = query.order_by(
        (Submission.actual_deadline < date.today()).desc(),
        Submission.actual_deadline.asc()
    )

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    submissions = result.scalars().all()

    return submissions


@router.get("/active", response_model=List[SubmissionWithDetails])
async def get_active_submissions(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить все активные работы (требующие внимания)

    Сортировка по срочности: просроченные, сегодня, ближайшие
    """
    query = """
    SELECT s.*, st.display_name as student_name, at.name as assignment_name
    FROM submissions s
    JOIN students st ON s.student_id = st.id
    JOIN assignment_types at ON s.assignment_type_id = at.id
    WHERE s.status NOT IN ('approved', 'rejected')
    ORDER BY
        CASE
            WHEN s.actual_deadline < CURRENT_DATE THEN 0  -- просроченные
            WHEN s.actual_deadline = CURRENT_DATE THEN 1  -- сегодня
            WHEN s.actual_deadline <= CURRENT_DATE + 3 THEN 2  -- скоро
            ELSE 3
        END,
        s.actual_deadline ASC
    """

    result = await db.execute(query)
    submissions = result.fetchall()

    return submissions


@router.get("/workload", response_model=WorkloadStats)
async def get_workload(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику загрузки преподавателя
    """
    # Работы на проверке
    pending_query = select(func.count(Submission.id)).where(
        Submission.status.in_(['submitted', 'form_reviewed'])
    )
    pending_result = await db.execute(pending_query)
    pending_review = pending_result.scalar()

    # Сдано сегодня
    today_query = select(func.count(Submission.id)).where(
        Submission.status == 'submitted',
        func.date(Submission.updated_at) == date.today()
    )
    today_result = await db.execute(today_query)
    submitted_today = today_result.scalar()

    # Дедлайны на этой неделе
    week_end = date.today() + timedelta(days=7)
    week_query = select(func.count(Submission.id)).where(
        Submission.actual_deadline.between(date.today(), week_end),
        Submission.status.notin_(['approved', 'rejected'])
    )
    week_result = await db.execute(week_query)
    deadline_this_week = week_result.scalar()

    # По типам работ
    type_query = """
    SELECT at.code, COUNT(s.id)
    FROM submissions s
    JOIN assignment_types at ON s.assignment_type_id = at.id
    WHERE s.status NOT IN ('approved', 'rejected')
    GROUP BY at.code
    """
    type_result = await db.execute(type_query)
    by_type = {row[0]: row[1] for row in type_result.fetchall()}

    # По статусам
    status_query = """
    SELECT status, COUNT(id)
    FROM submissions
    GROUP BY status
    """
    status_result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.fetchall()}

    return WorkloadStats(
        pending_review=pending_review,
        submitted_today=submitted_today,
        deadline_this_week=deadline_this_week,
        by_assignment_type=by_type,
        by_status=by_status
    )


@router.get("/deadlines", response_model=DeadlineStatus)
async def get_deadlines_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статус дедлайнов
    """
    query = """
    SELECT
        COUNT(*) FILTER (WHERE actual_deadline < CURRENT_DATE) as overdue,
        COUNT(*) FILTER (WHERE actual_deadline = CURRENT_DATE) as today,
        COUNT(*) FILTER (WHERE actual_deadline BETWEEN CURRENT_DATE + 1 AND CURRENT_DATE + 3) as soon,
        COUNT(*) FILTER (WHERE actual_deadline > CURRENT_DATE + 3) as normal
    FROM submissions
    WHERE status NOT IN ('approved', 'rejected')
    """

    result = await db.execute(query)
    row = result.fetchone()

    return DeadlineStatus(
        overdue=row[0] or 0,
        today=row[1] or 0,
        soon=row[2] or 0,
        normal=row[3] or 0,
        total=(row[0] or 0) + (row[1] or 0) + (row[2] or 0) + (row[3] or 0)
    )


@router.get("/{submission_id}", response_model=SubmissionWithDetails)
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить работу по ID с деталями (файлы, проверки, студент)
    """
    query = select(Submission).where(Submission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # TODO: Загрузить связанные файлы, проверки, студента

    return submission


@router.post("/", response_model=SubmissionResponse, status_code=201)
async def create_submission(
    submission_data: SubmissionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать новую работу

    Обычно создаётся автоматически при первой сдаче студентом.
    """
    # Получаем тип задания
    type_query = select(AssignmentType).where(AssignmentType.code == submission_data.assignment_type)
    type_result = await db.execute(type_query)
    assignment_type = type_result.scalar_one_or_none()

    if not assignment_type:
        raise HTTPException(status_code=400, detail="Invalid assignment type")

    # Определяем начальный этап
    stages = assignment_type.stages
    initial_stage = stages[0]['stage'] if stages else 'submit'

    # Рассчитываем дедлайн
    if not submission_data.base_deadline and stages:
        deadline_days = stages[0].get('deadline_days', 14)
        base_deadline = date.today() + timedelta(days=deadline_days)
    else:
        base_deadline = submission_data.base_deadline

    submission = Submission(
        student_id=submission_data.student_id,
        assignment_type_id=assignment_type.id,
        title=submission_data.title,
        description=submission_data.description,
        current_stage=initial_stage,
        status=SubmissionStatus.PENDING.value,
        base_deadline=base_deadline
    )

    db.add(submission)
    await db.flush()
    await db.refresh(submission)

    logger.info(
        "Submission created",
        submission_id=str(submission.id),
        student_id=submission_data.student_id,
        type=submission_data.assignment_type
    )

    return submission


@router.patch("/{submission_id}", response_model=SubmissionResponse)
async def update_submission(
    submission_id: str,
    submission_data: SubmissionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить работу

    Используется для:
    - Изменения статуса
    - Продления дедлайна
    - Выставления оценки
    """
    query = select(Submission).where(Submission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    update_data = submission_data.model_dump(exclude_unset=True)

    # Если статус меняется на approved/rejected, фиксируем дату завершения
    if 'status' in update_data and update_data['status'] in ['approved', 'rejected']:
        update_data['completed_at'] = date.today()

    for field, value in update_data.items():
        setattr(submission, field, value)

    await db.flush()
    await db.refresh(submission)

    logger.info(
        "Submission updated",
        submission_id=str(submission.id),
        changes=list(update_data.keys())
    )

    return submission


@router.post("/{submission_id}/advance-stage")
async def advance_stage(
    submission_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Перевести работу на следующий этап пайплайна
    """
    query = select(Submission).where(Submission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Получаем этапы
    type_query = select(AssignmentType).where(AssignmentType.id == submission.assignment_type_id)
    type_result = await db.execute(type_query)
    assignment_type = type_result.scalar_one()

    stages = assignment_type.stages
    current_idx = next(
        (i for i, s in enumerate(stages) if s['stage'] == submission.current_stage),
        -1
    )

    if current_idx == -1 or current_idx + 1 >= len(stages):
        raise HTTPException(status_code=400, detail="Cannot advance: already at final stage or invalid state")

    next_stage = stages[current_idx + 1]
    submission.current_stage = next_stage['stage']

    # Обновляем дедлайн для нового этапа
    if 'deadline_days' in next_stage:
        submission.base_deadline = date.today() + timedelta(days=next_stage['deadline_days'])

    await db.flush()

    logger.info(
        "Submission stage advanced",
        submission_id=str(submission.id),
        new_stage=submission.current_stage
    )

    return {"status": "ok", "new_stage": submission.current_stage}


# Модели для импорта
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base
from datetime import datetime


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)


class AssignmentType(Base):
    __tablename__ = "assignment_types"

    id = Column(UUID(as_uuid=True), primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    stages = Column(JSONB, default=[])
    artifact_type = Column(String(20))
    is_active = Column(Boolean, default=True)
