"""
DigitalTutor Bot - Students Handler (Updated)
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

def get_student_status_color(student, works):
    if not works:
        return "⚪", "Нет работ"
    now = datetime.utcnow()
    has_overdue = False
    has_close_deadline = False
    for work in works:
        if work.deadline:
            days_to_deadline = (work.deadline - now).days
            if days_to_deadline < 0:
                has_overdue = True
            elif days_to_deadline <= 3:
                has_close_deadline = True
    rejected_count = sum(1 for w in works if w.status == 'rejected')
    if has_overdue or rejected_count > 0:
        return "🔴", "Требует внимания"
    elif has_close_deadline:
        return "🟡", "Дедлайн близко"
    else:
        return "🟢", "В порядке"

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
            await message.answer("👥 Список студентов пуст", reply_markup=get_admin_menu())
            return

        text = "👥 <b>Список студентов</b>\n\n"
        kb = []

        for i, student in enumerate(students, 1):
            works_result = await session.execute(
                select(StudentWork).where(StudentWork.student_id == student.id)
            )
            works = works_result.scalars().all()
            status_emoji, _ = get_student_status_color(student, works)

            # Находим ближайший дедлайн
            closest = None
            for w in works:
                if w.deadline and (not closest or w.deadline < closest):
                    closest = w.deadline

            dl_str = ""
            if closest:
                days = (closest - datetime.utcnow()).days
                dl_str = f" | {days}д" if days >= 0 else f" | {abs(days)}д назад"

            text += f"{i}. {status_emoji} <b>{student.full_name or 'Без имени'}</b>{dl_str}\n"

            # Кнопки действий для студента
            kb.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {student.full_name or 'Без имени'}",
                    callback_data=f"student_detail:{student.id}"
                )
            ])

        # Фильтры
        kb.append([
            InlineKeyboardButton(text="🔴 Критичные", callback_data="filter:critical"),
            InlineKeyboardButton(text="🟡 Внимание", callback_data="filter:warning")
        ])
        kb.append([
            InlineKeyboardButton(text="🟢 В порядке", callback_data="filter:ok"),
            InlineKeyboardButton(text="⚪ Без работ", callback_data="filter:no_works")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("student_detail:"))
async def show_student_detail(callback: CallbackQuery):
    """Детальная карточка студента с работами и действиями"""
    student_id = callback.data.split(":")[1]

    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()

        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return

        # Получаем работы
        works_result = await session.execute(
            select(StudentWork).where(StudentWork.student_id == student.id)
        )
        works = works_result.scalars().all()

        # Формируем текст карточки
        text = f"""👤 <b>{student.full_name or 'Без имени'}</b>
📱 @{student.telegram_username or 'нет'}
🎓 Роль: {student.role or 'не указана'}

📊 <b>Статистика:</b>
• Всего работ: {len(works)}
• Завершено: {sum(1 for w in works if w.grade_classic)}
• На проверке: {sum(1 for w in works if w.status in ['submitted', 'under_review'])}

📋 <b>Артефакты:</b>
"""
        kb = []

        if not works:
            text += "\n<i>Нет работ</i>"
        else:
            for work in works:
                # Иконка статуса
                if work.grade_classic:
                    icon = "🟢"
                    status = f"Оценка: {work.grade_classic}"
                elif work.status == 'rejected':
                    icon = "🔴"
                    status = "Отклонена"
                elif work.deadline and work.deadline < datetime.utcnow():
                    icon = "🔴"
                    status = "Просрочена"
                else:
                    icon = "🟡"
                    status = "В работе"

                dl_str = ""
                if work.deadline:
                    days = (work.deadline - datetime.utcnow()).days
                    dl_str = f" | {'❗' if days < 0 else '⚠️' if days <= 3 else '📅'} {work.deadline.strftime('%d.%m')}"

                text += f"\n{icon} <b>{work.title or 'Без названия'}</b>\n   └ {status}{dl_str}"

                # Кнопка для каждой работы
                kb.append([
                    InlineKeyboardButton(
                        text=f"📄 {work.title[:25] if work.title else 'Без названия'}",
                        callback_data=f"admin_work:{work.id}"
                    ),
                    InlineKeyboardButton(
                        text="⬇️ Файл",
                        callback_data=f"download_work:{work.id}"
                    )
                ])

        # Действия со студентом
        text += "\n\n<b>💬 Действия:</b>"

        kb.append([
            InlineKeyboardButton(
                text="💬 Написать сообщение",
                callback_data=f"message_student:{student.id}"
            )
        ])
        kb.append([
            InlineKeyboardButton(
                text="📨 Перейти в переписку",
                callback_data=f"chat_history:{student.id}"
            )
        ])
        kb.append([
            InlineKeyboardButton(text="👥 К списку", callback_data="students:back")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=kb)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("message_student:"))
async def message_student_prompt(callback: CallbackQuery):
    """Запросить текст сообщения для студента"""
    student_id = callback.data.split(":")[1]

    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()

        if student:
            await callback.message.answer(
                f"💬 <b>Сообщение для {student.full_name or 'студента'}</b>\n\n"
                f"Напишите текст сообщения ответом на это сообщение:",
                parse_mode="HTML"
            )
            # Сохраняем ID студента в контексте (можно через FSM)

    await callback.answer()


@router.callback_query(F.data.startswith("chat_history:"))
async def show_chat_history(callback: CallbackQuery):
    """Показать историю переписки со студентом"""
    student_id = callback.data.split(":")[1]

    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()

        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return

        # Здесь можно загрузить историю из БД если есть таблица messages
        text = f"""📨 <b>Переписка с {student.full_name or 'студентом'}</b>

📱 Telegram: @{student.telegram_username or 'не указан'}

<i>История сообщений будет загружена...</i>

Напишите сообщение для отправки:
"""
        kb = [[InlineKeyboardButton(text="👤 Назад к карточке", callback_data=f"student_detail:{student_id}")]]

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "students:back")
async def back_to_students(callback: CallbackQuery):
    """Вернуться к списку студентов"""
    await show_students_menu(callback.message)
    await callback.answer()
