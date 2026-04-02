"""
DigitalTutor Bot - Start Handler
Обработчик команды /start и главного меню
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select
from datetime import datetime

from bot.keyboards import get_main_menu, get_admin_menu
from bot.templates.messages import Messages

logger = logging.getLogger(__name__)
router = Router()

# Admin IDs
ADMIN_IDS = [502621151]


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    from bot.models import AsyncSessionContext, User
    
    telegram_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            menu = get_admin_menu() if is_admin(telegram_id) else get_main_menu()
            role_name = user.role if user.role else "Студент"
            await message.answer(
                Messages.WELCOME_BACK.format(
                    name=user.full_name or full_name,
                    role=role_name
                ),
                reply_markup=menu,
                parse_mode="HTML"
            )
        else:
            from .registration import start_registration
            await start_registration(message)


@router.message(F.text == "🔙 Студенческое меню")
async def back_to_student_menu(message: Message):
    """Вернуться в студенческое меню"""
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu()
    )


@router.message(F.text.in_(["📊 Статус", "📊 Статистика системы"]))
async def show_status(message: Message):
    """Показать статус/статистику"""
    telegram_id = message.from_user.id
    
    if is_admin(telegram_id):
        await show_admin_stats(message)
        return
    
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
            await message.answer(
                "📊 <b>Статистика</b>\n\nПока нет данных. Сдайте первую работу!",
                reply_markup=get_main_menu(),
                parse_mode="HTML"
            )
            return
        
        total = len(works)
        accepted = len([w for w in works if w.status == 'accepted'])
        in_review = len([w for w in works if w.status in ['submitted', 'in_review']])
        revision = len([w for w in works if w.status == 'revision_required'])
        draft = len([w for w in works if w.status == 'draft'])
        
        upcoming = [w for w in works if w.deadline and w.deadline > datetime.utcnow()]
        upcoming.sort(key=lambda x: x.deadline)
        
        deadlines_text = ""
        if upcoming[:3]:
            for work in upcoming[:3]:
                days_left = (work.deadline - datetime.utcnow()).days
                emoji = "🚨" if days_left <= 1 else "⚠️" if days_left <= 3 else "📅"
                deadlines_text += f"{emoji} <b>{work.title[:30]}...</b> — {work.deadline.strftime('%d.%m.%Y')}\n"
        else:
            deadlines_text = "Нет предстоящих дедлайнов 🎉"
        
        from bot.templates.messages import Messages
        await message.answer(
            Messages.STATUS_STATS.format(
                total=total,
                accepted=accepted,
                in_review=in_review,
                revision=revision,
                draft=draft,
                deadlines=Messages.STATUS_DEADLINES.format(deadlines_list=deadlines_text)
            ),
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )


async def show_admin_stats(message: Message):
    """Показать админскую статистику"""
    from bot.models import AsyncSessionContext, StudentWork, User
    
    async with AsyncSessionContext() as session:
        result = await session.execute(select(StudentWork))
        works = result.scalars().all()
        
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        total_works = len(works)
        total_students = len(users)
        
        status_counts = {}
        for work in works:
            status_counts[work.status] = status_counts.get(work.status, 0) + 1
        
        text = "📊 <b>Статистика системы</b>\n\n"
        text += f"👥 Всего студентов: <b>{total_students}</b>\n"
        text += f"📁 Всего работ: <b>{total_works}</b>\n\n"
        text += "<b>По статусам:</b>\n"
        
        STATUS_INFO = {
            "draft": {"emoji": "📝", "name": "Черновик"},
            "submitted": {"emoji": "📤", "name": "Отправлена"},
            "in_review": {"emoji": "👀", "name": "На проверке"},
            "revision_required": {"emoji": "🔄", "name": "Требует доработки"},
            "accepted": {"emoji": "✅", "name": "Принята"},
            "rejected": {"emoji": "❌", "name": "Отклонена"},
        }
        
        for status, info in STATUS_INFO.items():
            count = status_counts.get(status, 0)
            if count > 0:
                text += f"{info['emoji']} {info['name']}: <b>{count}</b>\n"
        
        await message.answer(text, reply_markup=get_admin_menu(), parse_mode="HTML")


@router.message(F.text == "❓ Помощь")
async def show_help(message: Message):
    """Показать справку"""
    await message.answer(
        Messages.HELP_TEXT,
        reply_markup=get_main_menu() if not is_admin(message.from_user.id) else get_admin_menu(),
        parse_mode="HTML"
    )
