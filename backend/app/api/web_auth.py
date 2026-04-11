"""
DigitalTutor Backend - Web Authentication Module
Handles student web login (via Telegram code or QR), admin login, and code generation.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_
from jose import jwt, JWTError

from app.core.database import AsyncSessionLocal

# ==================== Config ====================
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-2024")
JWT_ALGORITHM = "HS256"
MASTER_CODE = os.getenv("MASTER_CODE", "ADMIN-2024")
WEB_SESSION_DURATION = 90  # minutes (1.5 hours)


# ==================== Models ====================
class WebLoginRequest(BaseModel):
    code: str


class AdminLoginRequest(BaseModel):
    master_code: str


class GenerateCodeRequest(BaseModel):
    student_id: str


# ==================== Router ====================
router = APIRouter()


async def _create_jwt(payload: dict, expires_minutes: int = WEB_SESSION_DURATION) -> str:
    """Create a JWT token with expiration."""
    exp = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload.update({"exp": exp, "jti": str(uuid4())})
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def _get_db():
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        yield session


def _get_user_table():
    """Lazy import to avoid circular dependencies."""
    from app.models.models import User, WebAuthCode
    return User, WebAuthCode


# ==================== Student Web Login ====================
@router.post("/web-login")
async def student_web_login(request: WebLoginRequest):
    """
    Validate a student access code (from Telegram bot or QR code).
    Returns JWT token and user info on success.
    """
    User, WebAuthCode = _get_user_table()

    code = request.code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Код не указан")

    async with AsyncSessionLocal() as session:
        # Look up the code
        stmt = select(WebAuthCode).where(
            and_(
                WebAuthCode.code == code,
                WebAuthCode.is_used == False,
                WebAuthCode.expires_at > datetime.now(timezone.utc),
            )
        )
        result = await session.execute(stmt)
        auth_code = result.scalar_one_or_none()

        if not auth_code:
            raise HTTPException(status_code=401, detail="Неверный код или код истёк")

        # Mark code as used
        auth_code.is_used = True
        auth_code.used_at = datetime.now(timezone.utc)
        await session.commit()

        # Get user
        stmt = select(User).where(User.id == auth_code.user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="Пользователь не найден или деактивирован")

        # Create JWT
        token = await _create_jwt({
            "user_id": str(user.id),
            "telegram_id": user.telegram_id,
            "role": "student",
            "full_name": user.full_name,
        })

        return {
            "valid": True,
            "token": token,
            "user": {
                "id": str(user.id),
                "telegram_id": user.telegram_id,
                "telegram_username": user.telegram_username,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "group_name": user.group_name,
                "course": user.course,
                "is_active": user.is_active,
                "yandex_folder": user.yandex_folder,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        }


# ==================== Admin Login ====================
@router.post("/admin-login")
async def admin_web_login(request: AdminLoginRequest):
    """
    Validate admin master code.
    Returns JWT token on success.
    """
    if request.master_code.strip() != MASTER_CODE:
        raise HTTPException(status_code=401, detail="Неверный мастер-код")

    token = await _create_jwt({
        "user_id": "admin",
        "role": "admin",
        "full_name": "Преподаватель",
    }, expires_minutes=480)  # 8 hours for admin

    return {
        "valid": True,
        "token": token,
    }


# ==================== Generate Access Code ====================
@router.post("/generate-code")
async def generate_access_code(request: GenerateCodeRequest):
    """
    Generate a one-time access code for a student (for QR code / manual entry).
    Called by admin panel.
    """
    User, WebAuthCode = _get_user_table()

    async with AsyncSessionLocal() as session:
        # Verify student exists
        stmt = select(User).where(User.id == request.student_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Студент не найден")

        # Generate code: DT-XXXXXX format
        code = f"DT-{secrets.token_hex(4).upper()}"

        # Create auth code record
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=WEB_SESSION_DURATION)

        auth_code = WebAuthCode(
            id=uuid4(),
            user_id=user.id,
            code=code,
            generated_by="admin",
            expires_at=expires_at,
            is_used=False,
        )
        session.add(auth_code)
        await session.commit()
        await session.refresh(auth_code)

        return {
            "code": code,
            "qr_data": code,  # In production, embed full JSON
            "student_name": user.full_name,
            "expires_at": expires_at.isoformat(),
        }


# ==================== Bot-side: Generate code for student ====================
@router.post("/bot-generate-code")
async def bot_generate_code(telegram_id: int):
    """
    Generate a web access code for a student, called by the Telegram bot.
    This is how the bot provides codes to students.
    """
    User, WebAuthCode = _get_user_table()

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        code = f"DT-{secrets.token_hex(4).upper()}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=WEB_SESSION_DURATION)

        auth_code = WebAuthCode(
            id=uuid4(),
            user_id=user.id,
            code=code,
            generated_by="bot",
            expires_at=expires_at,
            is_used=False,
        )
        session.add(auth_code)
        await session.commit()

        return {
            "code": code,
            "expires_at": expires_at.isoformat(),
            "expires_in_minutes": WEB_SESSION_DURATION,
        }
