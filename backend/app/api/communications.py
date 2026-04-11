from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.models import Communication

router = APIRouter()

@router.get("/work/{work_id}")
async def get_work_communications(work_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Communication)
        .where(Communication.work_id == work_id)
        .order_by(Communication.created_at.desc())
    )
    communications = result.scalars().all()
    
    return [{
        "id": str(c.id),
        "content": c.content,
        "content_transcription": c.content_transcription,
        "message_type": c.message_type,
        "channel": c.channel,
        "is_read": c.is_read,
        "created_at": c.created_at
    } for c in communications]

@router.post("/")
async def create_communication(data: dict, db: AsyncSession = Depends(get_db)):
    comm = Communication(**data)
    db.add(comm)
    await db.commit()
    return {"id": str(comm.id), "status": "created"}
