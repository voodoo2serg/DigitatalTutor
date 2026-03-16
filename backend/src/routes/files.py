"""
Files API Routes
Управление загрузкой и хранением файлов
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import hashlib
import io
import structlog

from src.database import get_db
from src.models.schemas import FileResponse, FileUploadResponse

router = APIRouter()
logger = structlog.get_logger()

# MinIO клиент будет инициализирован в main.py или через dependency
# minio_client = Minio(...)


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    submission_id: str,
    stage: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузить файл для работы

    Файл сохраняется в MinIO с версионируемым путём.
    Автоматически вычисляется SHA256 checksum.
    """
    # Читаем содержимое файла
    content = await file.read()
    file_size = len(content)

    # Вычисляем checksum
    checksum = hashlib.sha256(content).hexdigest()

    # Проверяем, не загружен ли уже такой файл
    existing_query = select(File).where(File.checksum_sha256 == checksum)
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="This file has already been uploaded"
        )

    # Определяем путь в MinIO
    # TODO: Использовать generate_file_path функцию из БД
    storage_path = f"student-files/{submission_id}/{stage}/{file.filename}"

    # Загружаем в MinIO
    # await minio_client.put_object(
    #     bucket_name="student-files",
    #     object_name=storage_path,
    #     data=io.BytesIO(content),
    #     length=file_size,
    #     content_type=file.content_type
    # )

    # Определяем версию
    version_query = select(File).where(
        File.submission_id == submission_id,
        File.stage == stage
    ).order_by(File.version_number.desc())
    version_result = await db.execute(version_query)
    last_version = version_result.scalar_one_or_none()
    version_number = (last_version.version_number + 1) if last_version else 1

    # Сохраняем метаданные в БД
    file_record = File(
        submission_id=submission_id,
        stage=stage,
        storage_path=storage_path,
        original_filename=file.filename,
        mime_type=file.content_type,
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        version_number=version_number,
        previous_version_id=last_version.id if last_version else None,
        uploaded_by_telegram_id=0,  # TODO: Получить из контекста
    )

    db.add(file_record)
    await db.flush()
    await db.refresh(file_record)

    logger.info(
        "File uploaded",
        file_id=str(file_record.id),
        filename=file.filename,
        size=file_size,
        checksum=checksum[:16] + "..."
    )

    return FileUploadResponse(
        id=str(file_record.id),
        filename=file.filename,
        size=file_size,
        checksum=checksum,
        message=f"File uploaded successfully. Version {version_number}"
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file_info(
    file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о файле
    """
    query = select(File).where(File.id == file_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return file


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Скачать файл из хранилища
    """
    query = select(File).where(File.id == file_id)
    result = await db.execute(query)
    file = result.scalar_one_or_none()

    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Получаем файл из MinIO
    # response = await minio_client.get_object(
    #     bucket_name="student-files",
    #     object_name=file.storage_path
    # )

    # return StreamingResponse(
    #     response.stream(),
    #     media_type=file.mime_type,
    #     headers={
    #         "Content-Disposition": f'attachment; filename="{file.original_filename}"'
    #     }
    # )

    # Заглушка для разработки
    return {"message": "Download not implemented yet", "path": file.storage_path}


@router.get("/{file_id}/versions", response_model=List[FileResponse])
async def get_file_versions(
    file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю версий файла
    """
    # Находим текущий файл
    query = select(File).where(File.id == file_id)
    result = await db.execute(query)
    current_file = result.scalar_one_or_none()

    if not current_file:
        raise HTTPException(status_code=404, detail="File not found")

    # Получаем все версии для этой работы и этапа
    versions_query = select(File).where(
        File.submission_id == current_file.submission_id,
        File.stage == current_file.stage
    ).order_by(File.version_number)

    versions_result = await db.execute(versions_query)
    versions = versions_result.scalars().all()

    return versions


@router.get("/{file_id}/compare/{other_file_id}")
async def compare_versions(
    file_id: str,
    other_file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Сравнить две версии файла

    Возвращает информацию об отличиях (для текстовых документов).
    """
    # Получаем оба файла
    query = select(File).where(File.id.in_([file_id, other_file_id]))
    result = await db.execute(query)
    files = result.scalars().all()

    if len(files) != 2:
        raise HTTPException(status_code=404, detail="One or both files not found")

    file1, file2 = files

    return {
        "file1": {
            "id": str(file1.id),
            "filename": file1.original_filename,
            "checksum": file1.checksum_sha256,
            "uploaded_at": file1.uploaded_at.isoformat()
        },
        "file2": {
            "id": str(file2.id),
            "filename": file2.original_filename,
            "checksum": file2.checksum_sha256,
            "uploaded_at": file2.uploaded_at.isoformat()
        },
        "identical": file1.checksum_sha256 == file2.checksum_sha256,
        # TODO: Для текстовых документов - diff
    }


@router.get("/submission/{submission_id}", response_model=List[FileResponse])
async def list_submission_files(
    submission_id: str,
    stage: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить все файлы для работы
    """
    query = select(File).where(File.submission_id == submission_id)

    if stage:
        query = query.where(File.stage == stage)

    query = query.order_by(File.uploaded_at.desc())

    result = await db.execute(query)
    files = result.scalars().all()

    return files


# Модель для импорта
from sqlalchemy import Column, String, DateTime, Text, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from src.database import Base
from datetime import datetime


class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True)
    submission_id = Column(UUID(as_uuid=True), nullable=False)
    stage = Column(String(50), nullable=False)
    storage_path = Column(Text, nullable=False)
    original_filename = Column(Text, nullable=False)
    mime_type = Column(String(255))
    file_size_bytes = Column(BigInteger)
    checksum_sha256 = Column(String(64), nullable=False)
    version_number = Column(Integer, default=1)
    previous_version_id = Column(UUID(as_uuid=True))
    change_summary = Column(Text)
    uploaded_by_telegram_id = Column(BigInteger, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_archived_copy = Column(Integer, default=0)  # Boolean в SQLite
