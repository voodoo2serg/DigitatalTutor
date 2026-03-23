from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.models import User

router = APIRouter()

@router.get("/")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "full_name": u.full_name, "role": u.role} for u in users]

@router.get("/{telegram_id}")
async def get_user_by_telegram(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "role": user.role,
        "group_name": user.group_name
    }

@router.post("/")
async def create_user(user_data: dict, db: AsyncSession = Depends(get_db)):
    user = User(**user_data)
    db.add(user)
    await db.commit()
    return {"id": str(user.id), "status": "created"}
