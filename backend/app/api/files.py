from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import os

from app.core.database import get_db
from app.core.config import settings
from app.models.models import File, StudentWork

router = APIRouter()

@router.post("/upload/{work_id}")
async def upload_file(
    work_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Check work exists
    result = await db.execute(select(StudentWork).where(StudentWork.id == work_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = f"/app/uploads/{unique_filename}"
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create DB record
    db_file = File(
        work_id=work_id,
        filename=unique_filename,
        original_name=file.filename,
        mime_type=file.content_type,
        size_bytes=len(content),
        storage_type='local',
        storage_path=file_path
    )
    db.add(db_file)
    await db.commit()
    
    return {
        "id": str(db_file.id),
        "filename": unique_filename,
        "original_name": file.filename,
        "size": len(content)
    }

@router.get("/work/{work_id}")
async def list_work_files(work_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(File).where(File.work_id == work_id))
    files = result.scalars().all()
    
    return [{
        "id": str(f.id),
        "original_name": f.original_name,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "created_at": f.created_at,
        "ai_analysis_status": f.ai_analysis_status
    } for f in files]
