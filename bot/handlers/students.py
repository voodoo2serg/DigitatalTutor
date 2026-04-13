"""
DigitalTutor Bot - Students Handler
Просмотр списка студентов и работ с ними
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, desc
from datetime import datetime

from bot.keyboards import get_admin_menu
from bot.config import config
from bot.models import AsyncSessionContext, User, StudentWork, Communication

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "👥 Студенты")
async def show_students_list(message: Message, state: FSMContext):
    """Показать список всех студентов"""
    telegram_id = message.from_user.id
    
    if telegram_id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой функции.")
        return
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(
                User.role.in_(['student', 'aspirant'])
            ).order_by(User.full_name)
        )
        students = result.scalars().all()
        
        if not students:
            await message.answer("❌ Нет зарегистрированных студентов.")
            return
        
        text = "<b>👥 Список студентов</b>\n\n"
        text += f"Всего: {len(students)}\n\n"
        text += "Выберите студента для действий:\n"
        
        keyboard = []
        for student in students[:30]:
            name = student.full_name or f"User_{student.telegram_id}"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{name}",
                    callback_data=f"student_actions:{student.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="« Назад", callback_data="admin_back")])
        
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("student_actions:"))
async def show_student_actions(callback: CallbackQuery, state: FSMContext):
    """Показать доступные действия со студентом"""
    student_id = callback.data.split(":")[1]
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return
        
        # Считаем непрочитанные сообщения
        unread_result = await session.execute(
            select(Communication).where(
                Communication.to_user_id == student_id,
                Communication.from_student == True,
                Communication.is_read == False
            )
        )
        unread_count = len(unread_result.scalars().all())
        
        # Получаем активные работы
        works_result = await session.execute(
            select(StudentWork).where(
                StudentWork.student_id == student_id,
                StudentWork.status.notin_(['accepted', 'rejected'])
            )
        )
        active_works = works_result.scalars().all()
        
        text = f"<b>👤 {student.full_name}</b>\n"
        text += f"Группа: {student.group_name or '—'}\n"
        text += f"Курс: {student.course or '—'}\n"
        text += f"Telegram: @{student.telegram_username or '—'}\n"
        text += f"ID: <code>{student.telegram_id}</code>\n\n"
        text += f"📋 Активных работ: {len(active_works)}\n"
        text += f"💬 Новых сообщений: {unread_count}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 История сообщений", callback_data=f"view_chat:{student_id}")],
            [InlineKeyboardButton(text="📝 Написать сообщение", callback_data=f"reply_to:{student_id}")],
            [InlineKeyboardButton(text="📋 Работы студента", callback_data=f"student_works:{student_id}")],
            [InlineKeyboardButton(text="✉️ Открыть в Telegram", url=f"tg://user?id={student.telegram_id}")],
            [InlineKeyboardButton(text="« Назад к списку", callback_data="back_to_students")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "back_to_students")
async def back_to_students_list(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку студентов"""
    await show_students_list(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Вернуться в админ-меню"""
    await state.clear()
    await callback.message.edit_text("Главное меню администратора:")
    await callback.message.answer(reply_markup=get_admin_menu())
    await callback.answer()
