from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.core.database import get_db
from app.models.models import StudentWork, WorkType, User

router = APIRouter()

@router.get("/")
async def list_works(
    student_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(StudentWork)
    if student_id:
        query = query.where(StudentWork.student_id == student_id)
    if status:
        query = query.where(StudentWork.status == status)
    
    result = await db.execute(query)
    works = result.scalars().all()
    
    return [{
        "id": str(w.id),
        "title": w.title,
        "status": w.status,
        "created_at": w.created_at,
        "ai_plagiarism_score": float(w.ai_plagiarism_score) if w.ai_plagiarism_score else None,
        "ai_structure_score": float(w.ai_structure_score) if w.ai_structure_score else None,
    } for w in works]

@router.get("/{work_id}")
async def get_work(work_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StudentWork).where(StudentWork.id == work_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    return {
        "id": str(work.id),
        "title": work.title,
        "description": work.description,
        "status": work.status,
        "ai_analysis_json": work.ai_analysis_json,
        "teacher_comment": work.teacher_comment,
        "created_at": work.created_at,
        "submitted_at": work.submitted_at,
        "deadline": work.deadline
    }

@router.post("/")
async def create_work(work_data: dict, db: AsyncSession = Depends(get_db)):
    work = StudentWork(**work_data)
    db.add(work)
    await db.commit()
    return {"id": str(work.id), "status": "created"}

@router.put("/{work_id}/status")
async def update_work_status(work_id: str, status: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StudentWork).where(StudentWork.id == work_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    work.status = status
    await db.commit()
    return {"id": str(work.id), "status": status}
