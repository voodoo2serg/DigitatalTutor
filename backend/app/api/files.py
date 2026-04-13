import os
import uuid as uuid_module
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import verify_token
from app.services.yandex_disk import YandexDiskService
from app.core.config import settings
from app.models.models import File, StudentWork

router = APIRouter()

@router.post("/upload/{work_id}")
async def upload_file(
    work_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db)
):
    """Upload file with duplicate check (filename + size + student)"""
    
    # Get work to find student
    from app.models.models import StudentWork, User
    result = await db.execute(select(StudentWork).where(StudentWork.id == uuid.UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Check for duplicates: filename + size + student
    file_content = await file.read()
    file_size = len(file_content)
    file.filename = file.filename or "unnamed"
    
    # Reset file position for later use
    await file.seek(0)
    
    # Check duplicates
    duplicate_result = await db.execute(
        select(File, StudentWork)
        .join(StudentWork, File.work_id == StudentWork.id)
        .where(StudentWork.student_id == work.student_id)
        .where(File.original_name == file.filename)
        .where(File.size_bytes == file_size)
        .order_by(File.created_at.desc())
        .limit(1)
    )
    duplicate = duplicate_result.first()
    
    if duplicate:
        file_obj, dup_work = duplicate
        raise HTTPException(
            status_code=409,
            detail={
                "error": "DUPLICATE_FILE",
                "message": "Файл с таким именем и размером уже загружен",
                "existing_file_id": str(file_obj.id),
                "existing_work_id": str(dup_work.id),
                "existing_work_title": dup_work.title,
                "uploaded_at": file_obj.created_at.isoformat() if file_obj.created_at else None
            }
        )
    # Check work exists
    result = await db.execute(select(StudentWork).where(StudentWork.id == uuid.UUID(work_id)))
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
        work_id=uuid.UUID(work_id),
        filename=unique_filename,
        original_name=file.filename,
        mime_type=file.content_type,
        size_bytes=len(content),
        storage_type='minio',
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
    try:
        work_uuid = uuid_module.UUID(work_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid work_id format")
    result = await db.execute(select(File).where(File.work_id == work_uuid))
    files = result.scalars().all()
    
    return [{
        "id": str(f.id),
        "original_name": f.original_name,
        "mime_type": f.mime_type,
        "size_bytes": f.size_bytes,
        "created_at": f.created_at,
        "ai_analysis_status": f.ai_analysis_status
    } for f in files]

@router.get("/{file_id}/public-url")
async def get_file_public_url(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Получить публичную ссылку на файл из Яндекс.Диска"""
    # Получаем файл
    result = await db.execute(select(File).where(File.id == uuid.UUID(file_id)))
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Если файл на Яндекс.Диске
    if file.storage_type == 'yandex_disk' and file.yandex_file_path:
        yandex_token = os.getenv("YANDEX_DISK_TOKEN")
        if not yandex_token:
            raise HTTPException(status_code=500, detail="Yandex Disk token not configured")
        
        yandex = YandexDiskService(yandex_token)
        public_url = yandex.get_public_link(file.yandex_file_path)
        
        if public_url:
            return {
                "success": True,
                "public_url": public_url,
                "filename": file.original_name,
                "yandex_path": file.yandex_file_path
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to get public link")
    
    # Если файл в minio/local — возвращаем прямую ссылку через API
    elif file.storage_type == 'minio':
        return {
            "success": True,
            "download_url": f"/api/v1/files/{file_id}/download",
            "filename": file.original_name,
            "storage_type": "minio"
        }
    
    raise HTTPException(status_code=400, detail="Unsupported storage type")

@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Скачать файл"""
    from fastapi.responses import FileResponse, StreamingResponse
    
    result = await db.execute(select(File).where(File.id == uuid.UUID(file_id)))
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Если локальный файл
    if file.storage_type == 'minio' and file.storage_path and os.path.exists(file.storage_path):
        return FileResponse(
            path=file.storage_path,
            filename=file.original_name or file.filename,
            media_type=file.mime_type or 'application/octet-stream'
        )
    
    # Если Яндекс.Диск — редирект на публичную ссылку
    if file.storage_type == 'yandex_disk' and file.yandex_file_path:
        yandex_token = os.getenv("YANDEX_DISK_TOKEN")
        if yandex_token:
            yandex = YandexDiskService(yandex_token)
            public_url = yandex.get_public_link(file.yandex_file_path)
            if public_url:
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=public_url)
    
    raise HTTPException(status_code=404, detail="File not available for download")
