"""
Notifications API Routes
Управление уведомлениями и массовыми рассылками
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import date, timedelta
import structlog

from src.database import get_db
from src.models.schemas import (
    MassNotificationRequest, NotificationResponse,
    NotificationTemplateCreate
)

router = APIRouter()
logger = structlog.get_logger()


@router.get("/templates", response_model=List[dict])
async def list_templates(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список шаблонов уведомлений
    """
    query = select(NotificationTemplate).where(NotificationTemplate.is_active == True)
    result = await db.execute(query)
    templates = result.scalars().all()

    return templates


@router.post("/templates", response_model=dict, status_code=201)
async def create_template(
    template_data: NotificationTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создать новый шаблон уведомления
    """
    template = NotificationTemplate(**template_data.model_dump())
    db.add(template)
    await db.flush()

    return {"id": str(template.id), "code": template.code}


@router.post("/send-mass", response_model=dict)
async def send_mass_notification(
    request: MassNotificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Отправить массовую рассылку

    Фильтры поддерживают:
    - assignment_type: тип работы
    - stage: этап пайплайна
    - deadline_within_days: дедлайн в ближайшие N дней
    - status: статус работы
    """
    # Строим запрос для поиска подходящих работ
    query = """
    SELECT DISTINCT s.student_id, s.id as submission_id
    FROM submissions s
    JOIN students st ON s.student_id = st.id
    WHERE st.is_active = TRUE
    """

    params = {}
    filters = request.filter_criteria

    if filters.get("assignment_type"):
        query += " AND s.assignment_type_id = (SELECT id FROM assignment_types WHERE code = :assignment_type)"
        params["assignment_type"] = filters["assignment_type"]

    if filters.get("stage"):
        query += " AND s.current_stage = :stage"
        params["stage"] = filters["stage"]

    if filters.get("status"):
        query += " AND s.status = :status"
        params["status"] = filters["status"]

    if filters.get("deadline_within_days"):
        days = filters["deadline_within_days"]
        query += f" AND s.actual_deadline <= CURRENT_DATE + INTERVAL '{days} days'"
        query += " AND s.actual_deadline >= CURRENT_DATE"

    result = await db.execute(query, params)
    targets = result.fetchall()

    if not targets:
        return {"status": "no_targets", "message": "No students match the filter criteria"}

    # Получаем шаблон
    message_body = request.custom_message
    if request.template_code and not message_body:
        template_query = select(NotificationTemplate).where(
            NotificationTemplate.code == request.template_code
        )
        template_result = await db.execute(template_query)
        template = template_result.scalar_one_or_none()
        if template:
            message_body = template.template

    if not message_body:
        raise HTTPException(status_code=400, detail="Either template_code or custom_message is required")

    # Создаём записи уведомлений
    batch_id = str(uuid.uuid4())
    for target in targets:
        notification = Notification(
            student_id=target[0],
            submission_id=target[1],
            notification_type="mass_message",
            body=message_body,
            batch_id=batch_id,
            status="pending"
        )
        db.add(notification)

    await db.flush()

    # Запускаем отправку в фоне
    background_tasks.add_task(
        send_notifications_task,
        batch_id
    )

    logger.info(
        "Mass notification scheduled",
        batch_id=batch_id,
        targets_count=len(targets)
    )

    return {
        "status": "scheduled",
        "batch_id": batch_id,
        "targets_count": len(targets)
    }


@router.post("/reminders/send", response_model=dict)
async def send_deadline_reminders(
    background_tasks: BackgroundTasks,
    days: List[int] = [1, 3],  # За сколько дней напоминать
    db: AsyncSession = Depends(get_db)
):
    """
    Отправить напоминания о дедлайнах

    Автоматически вызывается по расписанию (cron).
    """
    results = {}

    for day in days:
        target_date = date.today() + timedelta(days=day)

        # Находим работы с дедлайном в указанный день
        query = """
        SELECT s.id, s.title, s.current_stage, st.telegram_id, st.display_name
        FROM submissions s
        JOIN students st ON s.student_id = st.id
        WHERE s.actual_deadline = :target_date
        AND s.status NOT IN ('approved', 'rejected')
        AND st.is_active = TRUE
        """

        result = await db.execute(query, {"target_date": target_date})
        submissions = result.fetchall()

        results[day] = len(submissions)

        for sub in submissions:
            # TODO: Отправить реальное уведомление через Telegram
            logger.info(
                "Reminder sent",
                student_name=sub[4],
                deadline_days=day,
                submission_title=sub[1]
            )

    return {"status": "ok", "sent": results}


@router.get("/history", response_model=List[NotificationResponse])
async def get_notification_history(
    student_id: str = None,
    batch_id: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю уведомлений
    """
    query = select(Notification)

    if student_id:
        query = query.where(Notification.student_id == student_id)
    if batch_id:
        query = query.where(Notification.batch_id == batch_id)

    query = query.order_by(Notification.created_at.desc()).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return notifications


async def send_notifications_task(batch_id: str):
    """
    Background task для отправки уведомлений
    """
    # TODO: Реальная отправка через Telegram API
    logger.info("Sending notifications", batch_id=batch_id)


# Модели
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.database import Base
from datetime import datetime
import uuid


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(UUID(as_uuid=True), primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    template = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True)
    student_id = Column(UUID(as_uuid=True))
    submission_id = Column(UUID(as_uuid=True))
    template_id = Column(UUID(as_uuid=True))
    notification_type = Column(String(50), nullable=False)
    channel = Column(String(50), default='telegram')
    subject = Column(Text)
    body = Column(Text, nullable=False)
    status = Column(String(50), default='pending')
    sent_at = Column(DateTime)
    error_message = Column(Text)
    batch_id = Column(UUID(as_uuid=True))
    filter_criteria = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
