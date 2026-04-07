"""
DigitalTutor Bot - Students Handler (Critical Fix)
Fixed: DB field mismatch, telegram_id support, backward compatibility
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from bot.config import config
from bot.keyboards import get_admin_menu
from bot.services.db import AsyncSessionContext
from bot.models import User, StudentWork

logger = logging.getLogger(__name__)
router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

def get_student_status_color(works):
    """Определить цвет статуса студента"""
    if not works:
        return "⚪"
    now = datetime.utcnow()
    has_overdue = any(w.deadline and w.deadline < now for w in works)
    has_close = any(w.deadline and 0 <= (w.deadline - now).days <= 3 for w in works)
    rejected = sum(1 for w in works if w.status == 'rejected')
    
    if has_overdue or rejected > 0:
        return "🔴"
    elif has_close:
        return "🟡"
    return "🟢"

def get_work_status_icon(work):
    """Иконка статуса работы (БЕЗ обращения к grade_classic!)"""
    if work.status == 'approved':
        return "🟢"
    elif work.status == 'rejected':
        return "🔴"
    elif work.deadline and work.deadline < datetime.utcnow():
        return "🔴"
    elif work.status in ['submitted', 'under_review']:
        return "🟡"
    return "⚪"

@router.message(F.text == "👥 Студенты")
async def show_students_menu(message: Message):
    telegram_id = message.from_user.id
    if not is_admin(telegram_id):
        await message.answer("⛔ У вас нет доступа.")
        return
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.role.isnot(None)).order_by(User.full_name)
        )
        students = result.scalars().all()
        
        if not students:
            await message.answer("👥 Список студентов пуст")
            return
        
        text = "👥 <b>Список студентов</b>\n\n"
        kb = []
        
        for i, student in enumerate(students, 1):
            works_result = await session.execute(
                select(StudentWork).where(StudentWork.student_id == student.id)
            )
            works = works_result.scalars().all()
            status_emoji = get_student_status_color(works)
            
            closest = None
            for w in works:
                if w.deadline and (not closest or w.deadline < closest):
                    closest = w.deadline
            
            dl_str = ""
            if closest:
                days = (closest - datetime.utcnow()).days
                dl_str = f" ({days}д)" if days >= 0 else f" ({abs(days)}д назад)"
            
            text += f"{i}. {status_emoji} {student.full_name or 'Без имени'}{dl_str}\n"
            
            kb.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {student.full_name or 'Без имени'}",
                    callback_data=f"student:{student.id}"
                )
            ])
        
        kb.append([
            InlineKeyboardButton(text="🔴 Критичные", callback_data="filter:critical"),
            InlineKeyboardButton(text="🟡 Внимание", callback_data="filter:warning")
        ])
        kb.append([
            InlineKeyboardButton(text="🟢 В порядке", callback_data="filter:ok"),
            InlineKeyboardButton(text="⚪ Без работ", callback_data="filter:no_works")
        ])
        
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")


@router.callback_query(F.data.startswith("student:"))
async def show_student_card(callback: CallbackQuery):
    """Карточка студента с исправленными кнопками связи"""
    student_id = callback.data.split(":")[1]
    
    async with AsyncSessionContext() as session:
        result = await session.execute(select(User).where(User.id == student_id))
        student = result.scalar_one_or_none()
        
        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return
        
        works_result = await session.execute(
            select(StudentWork).where(StudentWork.student_id == student.id)
        )
        works = works_result.scalars().all()
        
        # Проверяем статус работ (БЕЗ grade_classic!)
        approved_count = sum(1 for w in works if w.status == 'approved')
        review_count = sum(1 for w in works if w.status in ['submitted', 'under_review'])
        
        text = f"""👤 <b>{student.full_name or 'Без имени'}</b>

📱 Telegram: @{student.telegram_username or 'не указан'}
🆔 ID: {student.telegram_id or 'неизвестен'}
🎓 Роль: {student.role or 'не указана'}

📊 <b>Статистика:</b>
• Всего работ: {len(works)}
• Завершено: {approved_count}
• На проверке: {review_count}
"""
        
        kb = []
        
        # 💬 Написать в Telegram (через username ИЛИ id)
        if student.telegram_username:
            kb.append([
                InlineKeyboardButton(
                    text="💬 Написать в Telegram",
                    url=f"https://t.me/{student.telegram_username}"
                )
            ])
        elif student.telegram_id:
            # Используем tg:// ссылку по ID
            kb.append([
                InlineKeyboardButton(
                    text="💬 Открыть диалог в Telegram",
                    url=f"tg://user?id={student.telegram_id}"
                )
            ])
        
        # 🤖 Написать через бота
        kb.append([
            InlineKeyboardButton(
                text="🤖 Написать через бота",
                callback_data=f"msg_via_bot:{student.id}"
            )
        ])
        
        # Работы
        if works:
            kb.append([InlineKeyboardButton(text="📋 Все работы студента", callback_data=f"student_works:{student.id}")])
        
        kb.append([InlineKeyboardButton(text="👥 К списку студентов", callback_data="back_to_list")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("msg_via_bot:"))
async def message_via_bot_prompt(callback: CallbackQuery):
    """Запрос текста для отправки через бота"""
    student_id = callback.data.split(":")[1]
    
    async with AsyncSessionContext() as session:
        result = await session.execute(select(User).where(User.id == student_id))
        student = result.scalar_one_or_none()
        
        if student:
            text = f"""🤖 <b>Сообщение через бота</b>

Для: {student.full_name or 'студент'}

Напишите текст сообщения ответом на это сообщение.

<i>Сообщение будет отправлено студенту.</i>"""
            
            kb = [[InlineKeyboardButton(text="❌ Отмена", callback_data=f"student:{student_id}")]]
            
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery):
    await show_students_menu(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("filter:"))
async def filter_students(callback: CallbackQuery):
    """Фильтрация студентов"""
    filter_type = callback.data.split(":")[1]
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.role.isnot(None)).order_by(User.full_name)
        )
        all_students = result.scalars().all()
        
        filtered = []
        for student in all_students:
            works_result = await session.execute(
                select(StudentWork).where(StudentWork.student_id == student.id)
            )
            works = works_result.scalars().all()
            status = get_student_status_color(works)
            
            if filter_type == "critical" and status == "🔴":
                filtered.append(student)
            elif filter_type == "warning" and status == "🟡":
                filtered.append(student)
            elif filter_type == "ok" and status == "🟢":
                filtered.append(student)
            elif filter_type == "no_works" and status == "⚪":
                filtered.append(student)
        
        if not filtered:
            await callback.answer("Нет студентов в этой категории", show_alert=True)
            return
        
        text = f"👥 <b>Фильтр</b>\n\n"
        kb = []
        
        for i, student in enumerate(filtered, 1):
            works_result = await session.execute(
                select(StudentWork).where(StudentWork.student_id == student.id)
            )
            works = works_result.scalars().all()
            status_emoji = get_student_status_color(works)
            
            text += f"{i}. {status_emoji} {student.full_name or 'Без имени'}\n"
            kb.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {student.full_name or 'Без имени'}",
                    callback_data=f"student:{student.id}"
                )
            ])
        
        kb.append([InlineKeyboardButton(text="👥 Сбросить фильтр", callback_data="back_to_list")])
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        await callback.answer()


# Обратная совместимость со старыми кнопками
@router.callback_query(F.data.startswith("message_student:"))
async def message_student_old(callback: CallbackQuery):
    await callback.message.answer("⚠️ Интерфейс обновлён. Нажмите 👥 Студенты заново.")
    await callback.answer()


@router.callback_query(F.data.startswith("student_detail:"))
async def student_detail_old(callback: CallbackQuery):
    student_id = callback.data.split(":")[1]
    callback.data = f"student:{student_id}"
    await show_student_card(callback)


@router.callback_query(F.data.startswith("chat_history:"))
async def chat_history_old(callback: CallbackQuery):
    student_id = callback.data.split(":")[1]
    callback.data = f"student:{student_id}"
    await show_student_card(callback)


@router.callback_query(F.data.startswith("student_works:"))
async def show_student_works(callback: CallbackQuery):
    """Показать все работы студента со статусами и файлами"""
    student_id = callback.data.split(":")[1]
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return
        
        works_result = await session.execute(
            select(StudentWork)
            .where(StudentWork.student_id == student.id)
            .order_by(StudentWork.created_at.desc())
        )
        works = works_result.scalars().all()
        
        if not works:
            await callback.answer("У студента нет работ", show_alert=True)
            return
        
        text = f"📋 <b>Работы: {student.full_name or 'Без имени'}</b>\n\n"
        kb = []
        
        for i, work in enumerate(works, 1):
            icon = get_work_status_icon(work)
            deadline_str = ""
            if work.deadline:
                days = (work.deadline - datetime.utcnow()).days
                if days < 0:
                    deadline_str = f" (просрочено {abs(days)}д)"
                elif days == 0:
                    deadline_str = " (сегодня!)"
                else:
                    deadline_str = f" (осталось {days}д)"
            
            text += f"{i}. {icon} <b>{work.title or 'Без названия'}</b>{deadline_str}\n"
            text += f"   Статус: {work.status or 'неизвестен'}\n\n"
            
            # Кнопки для каждой работы
            kb.append([
                InlineKeyboardButton(
                    text=f"{icon} {work.title[:25]}{'...' if len(work.title) > 25 else ''}",
                    callback_data=f"admin_work:{work.id}"
                )
            ])
        
        kb.append([InlineKeyboardButton(text="👤 К карточке студента", callback_data=f"student:{student_id}")])
        kb.append([InlineKeyboardButton(text="👥 К списку студентов", callback_data="back_to_list")])
        
        await callback.message.edit_text(
            text, 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
            parse_mode="HTML"
        )
        await callback.answer()
