"""
DigitalTutor Bot - Works Handler
Мои работы и управление ими
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from datetime import datetime

from bot.keyboards import get_main_menu, get_admin_menu
from bot.templates.messages import Messages

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = [502621151]

STATUS_INFO = {
    "draft": {"emoji": "📝", "name": "Черновик"},
    "submitted": {"emoji": "📤", "name": "Отправлена"},
    "in_review": {"emoji": "👀", "name": "На проверке"},
    "revision_required": {"emoji": "🔄", "name": "Требует доработки"},
    "accepted": {"emoji": "✅", "name": "Принята"},
    "rejected": {"emoji": "❌", "name": "Отклонена"},
}


@router.message(F.text == "📋 Мои работы")
async def list_my_works(message: Message):
    """Показать список работ студента"""
    telegram_id = message.from_user.id
    
    from bot.models import AsyncSessionContext, User, StudentWork
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(Messages.ERROR_REGISTRATION_INCOMPLETE)
            return
        
        result = await session.execute(
            select(StudentWork).where(StudentWork.student_id == user.id)
        )
        works = result.scalars().all()
        
        if not works:
            await message.answer(Messages.WORKS_EMPTY, reply_markup=get_main_menu())
            return
        
        status_counts = {}
        for work in works:
            status_counts[work.status] = status_counts.get(work.status, 0) + 1
        
        status_summary = ""
        for status, info in STATUS_INFO.items():
            count = status_counts.get(status, 0)
            if count > 0:
                status_summary += f"{info['emoji']} {info['name']}: <b>{count}</b>\n"
        
        await message.answer(
            Messages.WORKS_LIST_HEADER.format(status_summary=status_summary),
            parse_mode="HTML"
        )
        
        works_sorted = sorted(works, key=lambda x: x.created_at, reverse=True)[:5]
        
        for work in works_sorted:
            status_info = STATUS_INFO.get(work.status, {"emoji": "❓", "name": work.status})
            
            deadline_str = work.deadline.strftime("%d.%m.%Y") if work.deadline else "Не указан"
            submitted_str = work.submitted_at.strftime("%d.%m.%Y") if work.submitted_at else "Не сдана"
            
            text = Messages.WORK_CARD.format(
                emoji=status_info['emoji'],
                title=work.title[:50],
                work_type="Работа",
                status=status_info['name'],
                deadline=deadline_str,
                submitted_at=submitted_str
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📄 Подробнее", callback_data=f"work:{work.id}")]
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "📋 Все работы")
async def list_all_works(message: Message):
    """Админ: показать все работы"""
    telegram_id = message.from_user.id
    
    if telegram_id not in ADMIN_IDS:
        return
    
    from bot.models import AsyncSessionContext, StudentWork
    
    async with AsyncSessionContext() as session:
        result = await session.execute(select(StudentWork))
        works = result.scalars().all()
        
        if not works:
            await message.answer("📭 Работ пока нет", reply_markup=get_admin_menu())
            return
        
        status_counts = {}
        for work in works:
            status_counts[work.status] = status_counts.get(work.status, 0) + 1
        
        text = f"📊 <b>Всего работ: {len(works)}</b>\n\n"
        
        for status, info in STATUS_INFO.items():
            count = status_counts.get(status, 0)
            if count > 0:
                text += f"{info['emoji']} {info['name']}: <b>{count}</b>\n"
        
        await message.answer(text, reply_markup=get_admin_menu(), parse_mode="HTML")
        
        recent = sorted(works, key=lambda x: x.created_at, reverse=True)[:5]
        
        for work in recent:
            status_info = STATUS_INFO.get(work.status, {"emoji": "❓", "name": work.status})
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 Подробнее", callback_data=f"admin_work:{work.id}"),
                    InlineKeyboardButton(text="✍️ Рецензия", callback_data=f"review:{work.id}")
                ]
            ])
            
            text = f"{status_info['emoji']} <b>{work.title[:40]}</b>\n"
            text += f"├ Статус: {status_info['name']}\n"
            text += f"└ ID: <code>{work.id}</code>"
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
