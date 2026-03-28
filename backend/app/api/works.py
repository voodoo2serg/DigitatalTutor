"""
Extended Works API - Full functionality
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from uuid import UUID, uuid4
from datetime import datetime

from app.core.database import get_db
from app.models.models import StudentWork, User, File, Communication, WorkType
from app.api.auth import verify_token

router = APIRouter()


@router.get("/")
async def list_works(
    student_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Список работ с полной информацией"""
    query = select(StudentWork)
    
    if student_id:
        query = query.where(StudentWork.student_id == UUID(student_id))
    if status:
        query = query.where(StudentWork.status == status)
    
    query = query.order_by(desc(StudentWork.created_at))
    result = await db.execute(query)
    works = result.scalars().all()
    
    # Получаем имена студентов и типы работ
    student_ids = [w.student_id for w in works]
    students_result = await db.execute(select(User).where(User.id.in_(student_ids)))
    students = {str(s.id): s for s in students_result.scalars().all()}
    
    work_type_ids = [w.work_type_id for w in works if w.work_type_id]
    work_types_result = await db.execute(select(WorkType).where(WorkType.id.in_(work_type_ids)))
    work_types = {str(wt.id): wt for wt in work_types_result.scalars().all()}
    
    return [
        {
            "id": str(w.id),
            "student_id": str(w.student_id),
            "student_name": students.get(str(w.student_id)).full_name if students.get(str(w.student_id)) else None,
            "title": w.title,
            "description": w.description,
            "work_type_id": str(w.work_type_id) if w.work_type_id else None,
            "work_type_name": work_types.get(str(w.work_type_id)).name if w.work_type_id and work_types.get(str(w.work_type_id)) else "Другое",
            "status": w.status,
            "deadline": w.deadline.isoformat() if w.deadline else None,
            "submitted_at": w.submitted_at.isoformat() if w.submitted_at else None,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "updated_at": w.updated_at.isoformat() if w.updated_at else None,
            "ai_plagiarism_score": float(w.ai_plagiarism_score) if w.ai_plagiarism_score else None,
            "ai_structure_score": float(w.ai_structure_score) if w.ai_structure_score else None,
            "ai_formatting_score": float(w.ai_formatting_score) if w.ai_formatting_score else None,
            "teacher_comment": w.teacher_comment,
            "teacher_reviewed_at": w.teacher_reviewed_at.isoformat() if w.teacher_reviewed_at else None,
            "antiplag_originality_percent": float(w.antiplag_originality_percent) if w.antiplag_originality_percent else None,
        }
        for w in works
    ]


@router.get("/{work_id}")
async def get_work(
    work_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Получить детали работы"""
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Получаем студента
    student_result = await db.execute(select(User).where(User.id == work.student_id))
    student = student_result.scalar_one_or_none()
    
    # Получаем тип работы
    work_type_name = "Другое"
    if work.work_type_id:
        wt_result = await db.execute(select(WorkType).where(WorkType.id == work.work_type_id))
        wt = wt_result.scalar_one_or_none()
        if wt:
            work_type_name = wt.name
    
    return {
        "id": str(work.id),
        "student_id": str(work.student_id),
        "student_name": student.full_name if student else None,
        "student_telegram_id": student.telegram_id if student else None,
        "student_email": student.email if student else None,
        "student_telegram_username": student.telegram_username if student else None,
        "title": work.title,
        "description": work.description,
        "work_type_id": str(work.work_type_id) if work.work_type_id else None,
        "work_type_name": work_type_name,
        "status": work.status,
        "deadline": work.deadline.isoformat() if work.deadline else None,
        "submitted_at": work.submitted_at.isoformat() if work.submitted_at else None,
        "created_at": work.created_at.isoformat() if work.created_at else None,
        "updated_at": work.updated_at.isoformat() if work.updated_at else None,
        "ai_plagiarism_score": float(work.ai_plagiarism_score) if work.ai_plagiarism_score else None,
        "ai_structure_score": float(work.ai_structure_score) if work.ai_structure_score else None,
        "ai_formatting_score": float(work.ai_formatting_score) if work.ai_formatting_score else None,
        "ai_analysis_json": work.ai_analysis_json,
        "teacher_comment": work.teacher_comment,
        "teacher_reviewed_at": work.teacher_reviewed_at.isoformat() if work.teacher_reviewed_at else None,
        "antiplag_system": work.antiplag_system,
        "antiplag_originality_percent": float(work.antiplag_originality_percent) if work.antiplag_originality_percent else None,
        "antiplag_report_url": work.antiplag_report_url,
    }


@router.get("/{work_id}/files")
async def get_work_files(
    work_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Получить файлы работы"""
    result = await db.execute(select(File).where(File.work_id == UUID(work_id)).order_by(desc(File.created_at)))
    files = result.scalars().all()
    
    return [
        {
            "id": str(f.id),
            "original_name": f.original_name,
            "mime_type": f.mime_type,
            "size_bytes": f.size_bytes,
            "size_mb": round(f.size_bytes / (1024 * 1024), 2) if f.size_bytes else 0,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "ai_analysis_status": f.ai_analysis_status,
            "ai_analysis_result": f.ai_analysis_result,
        }
        for f in files
    ]


@router.get("/{work_id}/comments")
async def get_work_comments(
    work_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Получить комментарии к работе"""
    result = await db.execute(
        select(Communication)
        .where(Communication.work_id == UUID(work_id))
        .order_by(desc(Communication.created_at))
    )
    communications = result.scalars().all()
    
    # Получаем отправителей
    sender_ids = [c.sender_id for c in communications if c.sender_id]
    if sender_ids:
        senders_result = await db.execute(select(User).where(User.id.in_(sender_ids)))
        senders = {str(s.id): s for s in senders_result.scalars().all()}
    else:
        senders = {}
    
    return [
        {
            "id": str(c.id),
            "sender_id": str(c.sender_id) if c.sender_id else None,
            "sender_name": senders.get(str(c.sender_id)).full_name if c.sender_id and senders.get(str(c.sender_id)) else "Система",
            "message": c.message,
            "message_type": c.message_type,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "is_read": c.is_read,
        }
        for c in communications
    ]


@router.post("/{work_id}/comments")
async def add_work_comment(
    work_id: str,
    comment_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Добавить комментарий к работе"""
    # Проверяем существование работы
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Создаем коммуникацию
    new_comment = Communication(
        id=uuid4(),
        work_id=UUID(work_id),
        sender_id=UUID(comment_data.get("sender_id")) if comment_data.get("sender_id") else None,
        recipient_id=work.student_id,
        message=comment_data.get("message"),
        message_type=comment_data.get("message_type", "comment"),
        is_read=False,
        created_at=datetime.utcnow(),
    )
    
    db.add(new_comment)
    await db.commit()
    
    return {
        "id": str(new_comment.id),
        "message": new_comment.message,
        "created_at": new_comment.created_at.isoformat(),
    }


@router.get("/{work_id}/analysis")
async def get_work_analysis(
    work_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Получить результаты AI анализа работы"""
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    return {
        "work_id": str(work.id),
        "ai_plagiarism_score": float(work.ai_plagiarism_score) if work.ai_plagiarism_score else None,
        "ai_structure_score": float(work.ai_structure_score) if work.ai_structure_score else None,
        "ai_formatting_score": float(work.ai_formatting_score) if work.ai_formatting_score else None,
        "ai_analysis_json": work.ai_analysis_json,
        "antiplag_originality_percent": float(work.antiplag_originality_percent) if work.antiplag_originality_percent else None,
        "antiplag_system": work.antiplag_system,
        "antiplag_report_url": work.antiplag_report_url,
    }


@router.patch("/{work_id}")
async def update_work(
    work_id: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Обновить работу (статус, комментарий, оценки)"""
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Обновляем поля
    if 'title' in update_data:
        work.title = update_data['title']
    if 'description' in update_data:
        work.description = update_data['description']
    if 'status' in update_data:
        work.status = update_data['status']
        if update_data['status'] == 'submitted' and not work.submitted_at:
            work.submitted_at = datetime.utcnow()
    if 'teacher_comment' in update_data:
        work.teacher_comment = update_data['teacher_comment']
        work.teacher_reviewed_at = datetime.utcnow()
    if 'deadline' in update_data:
        work.deadline = update_data['deadline']
    if 'ai_plagiarism_score' in update_data:
        work.ai_plagiarism_score = update_data['ai_plagiarism_score']
    if 'ai_structure_score' in update_data:
        work.ai_structure_score = update_data['ai_structure_score']
    if 'ai_formatting_score' in update_data:
        work.ai_formatting_score = update_data['ai_formatting_score']
    if 'ai_analysis_json' in update_data:
        work.ai_analysis_json = update_data['ai_analysis_json']
    
    work.updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "success": True,
        "message": "Work updated",
        "work_id": str(work.id),
        "status": work.status,
        "updated_at": work.updated_at.isoformat(),
    }


@router.post("/")
async def create_work(
    work_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Создать новую работу"""
    # Validate required fields
    if not work_data.get("student_id"):
        raise HTTPException(status_code=400, detail="student_id is required")
    if not work_data.get("title"):
        raise HTTPException(status_code=400, detail="title is required")
    
    # Parse work_type_id
    work_type_id = None
    if work_data.get("work_type_id"):
        try:
            work_type_id = UUID(work_data["work_type_id"])
        except:
            work_type_id = UUID("d3e57c9e-ea11-44d0-bfd6-97b1b04a1482")  # Default: Другое
    else:
        work_type_id = UUID("d3e57c9e-ea11-44d0-bfd6-97b1b04a1482")  # Default: Другое
    
    # Parse deadline if provided
    deadline = None
    if work_data.get("deadline"):
        try:
            deadline = datetime.fromisoformat(work_data["deadline"].replace('Z', '+00:00'))
        except:
            pass
    
    # Create work
    new_work = StudentWork(
        id=uuid4(),
        student_id=UUID(work_data["student_id"]),
        work_type_id=work_type_id,
        title=work_data["title"],
        description=work_data.get("description"),
        status=work_data.get("status", "draft"),
        deadline=deadline,
        submitted_at=datetime.utcnow() if work_data.get("status") == "submitted" else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(new_work)
    await db.commit()
    
    return {
        "id": str(new_work.id),
        "student_id": str(new_work.student_id),
        "title": new_work.title,
        "status": new_work.status,
        "created_at": new_work.created_at.isoformat(),
        "submitted_at": new_work.submitted_at.isoformat() if new_work.submitted_at else None,
    }


@router.delete("/{work_id}")
async def delete_work(
    work_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Удалить работу (только если статус draft)"""
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    if work.status != "draft":
        raise HTTPException(status_code=400, detail="Can only delete works with status 'draft'")
    
    await db.delete(work)
    await db.commit()
    
    return {"success": True, "message": "Work deleted"}
