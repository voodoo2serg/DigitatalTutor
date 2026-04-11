"""
DigitalTutor Bot - Works Handler (Updated with Grading)
TICKET-3.1: Added grade button in admin work details
TICKET-3.2: Archive filter in works list
"""
import logging
import uuid
import os
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from sqlalchemy import select, update
from datetime import datetime

from bot.keyboards import get_main_menu, get_admin_menu
from bot.templates.messages import Messages
from bot.config import config
from bot.models import AsyncSessionContext, StudentWork, File

logger = logging.getLogger(__name__)
router = Router()

# Store message_id -> work_id mapping for admin replies
work_messages_map = {}

STATUS_INFO = {
    "draft": {"emoji": "📝", "name": "Черновик"},
    "submitted": {"emoji": "📤", "name": "Отправлена"},
    "in_review": {"emoji": "👀", "name": "На проверке"},
    "revision_required": {"emoji": "🔄", "name": "Требует доработки"},
    "accepted": {"emoji": "✅", "name": "Принята"},
    "rejected": {"emoji": "🗑️", "name": "Удалена"},
    "approved_for_publication": {"emoji": "📰", "name": "Согласована для публикации"},
    "admitted_to_defense": {"emoji": "🎓", "name": "Допущена к защите"},
    "graded": {"emoji": "⭐", "name": "Оценена"},
}


def get_work_messages_map():
    """Get reference to work_messages map for external modules"""
    return work_messages_map


@router.message(F.text == "📋 Мои работы")
async def list_my_works(message: Message):
    """Показать список работ студента (без архивных)"""
    telegram_id = message.from_user.id
    
    async with AsyncSessionContext() as session:
        from bot.models import User
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(Messages.ERROR_REGISTRATION_INCOMPLETE)
            return
        
        # TICKET-3.2: Exclude archived works for students
        result = await session.execute(
            select(StudentWork).where(
                StudentWork.student_id == user.id,
                StudentWork.status != "rejected",
                StudentWork.is_archived == False
            )
        )
        works = result.scalars().all()
        
        if not works:
            await message.answer(Messages.WORKS_EMPTY, reply_markup=get_main_menu())
            return
        
        await message.answer("📋 <b>Ваши работы:</b>", parse_mode="HTML")
        
        works_sorted = sorted(works, key=lambda x: x.created_at, reverse=True)[:5]
        
        for work in works_sorted:
            status_info = STATUS_INFO.get(work.status, {"emoji": "❓", "name": work.status})
            
            deadline_str = work.deadline.strftime("%d.%m.%Y") if work.deadline else "Не указан"
            submitted_str = work.submitted_at.strftime("%d.%m.%Y") if work.submitted_at else "Не сдана"
            
            text = f"""{status_info['emoji']} <b>{work.title[:50]}</b>
📊 Статус: {status_info['name']}
📅 Дедлайн: {deadline_str}
📤 Сдана: {submitted_str}"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📄 Подробнее", callback_data=f"work:{work.id}")]
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(F.text == "📋 Все работы")
async def list_all_works(message: Message):
    """Админ: показать активные работы (не архивные)"""
    telegram_id = message.from_user.id
    
    if telegram_id not in config.ADMIN_IDS:
        return
    
    async with AsyncSessionContext() as session:
        from bot.models import User
        # TICKET-3.2: Exclude archived works by default
        result = await session.execute(
            select(StudentWork).where(
                StudentWork.status != "rejected",
                StudentWork.is_archived == False
            )
            .order_by(StudentWork.created_at.desc()).limit(10)
        )
        works = result.scalars().all()
        
        if not works:
            await message.answer("Нет активных работ в системе", reply_markup=get_admin_menu())
            return
        
        await message.answer("📋 <b>Последние 10 активных работ:</b>", parse_mode="HTML")
        
        for work in works:
            status_info = STATUS_INFO.get(work.status, {"emoji": "❓", "name": work.status})
            
            result = await session.execute(
                select(User).where(User.id == work.student_id)
            )
            student = result.scalar_one_or_none()
            student_name = student.full_name if student else "Неизвестно"
            
            deadline_str = work.deadline.strftime("%d.%m.%Y") if work.deadline else "Не указан"
            
            text = f"""{status_info['emoji']} <b>{work.title[:40]}</b>
👤 {student_name}
📅 Дедлайн: {deadline_str}
📊 Статус: {status_info['name']}"""
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 Подробнее", callback_data=f"admin_work:{work.id}"),
                    InlineKeyboardButton(text="✍️ Рецензия", callback_data=f"review:{work.id}")
                ]
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("work:"))
async def show_work_details(callback_query: CallbackQuery):
    """Показать детали работы (для студента)"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await callback_query.answer("Работа не найдена", show_alert=True)
            return
        
        result = await session.execute(
            select(File).where(File.work_id == work_id)
        )
        files = result.scalars().all()
        
        status_info = STATUS_INFO.get(work.status, {"emoji": "❓", "name": work.status})
        
        deadline_str = work.deadline.strftime("%d.%m.%Y") if work.deadline else "Не указан"
        submitted_str = work.submitted_at.strftime("%d.%m.%Y %H:%M") if work.submitted_at else "Не сдана"
        
        # Generate file list
        files_text = ""
        keyboard_buttons = []
        
        if files:
            files_text = "\n📎 <b>Файлы:</b> (ответьте на сообщение для рецензии)\n"
            for i, f in enumerate(files, 1):
                files_text += f"{i}. {f.original_name or f.filename}\n"
                keyboard_buttons.append(
                    InlineKeyboardButton(
                        text=f"⬇️ Файл {i}",
                        callback_data=f"dl:{f.id}"
                    )
                )
        
        text = f"""{status_info['emoji']} <b>{work.title}</b>

📊 Статус: {status_info['name']}
📅 Дедлайн: {deadline_str}
📤 Сдана: {submitted_str}

📝 Описание:
{work.description or "Нет описания"}
{files_text}"""
        
        # Build keyboard
        keyboard_rows = []
        for btn in keyboard_buttons:
            keyboard_rows.append([btn])
        keyboard_rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
        sent_msg = await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
        # Store mapping for admin replies
        if callback_query.from_user.id in config.ADMIN_IDS:
            work_messages_map[sent_msg.message_id] = work_id
        
        await callback_query.answer()


@router.callback_query(F.data.startswith("admin_work:"))
async def show_admin_work_details(callback_query: CallbackQuery):
    """Показать детали работы для админа с кнопкой оценки (TICKET-3.1)"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    async with AsyncSessionContext() as session:
        from bot.models import User
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await callback_query.answer("Работа не найдена", show_alert=True)
            return
        
        result = await session.execute(
            select(User).where(User.id == work.student_id)
        )
        student = result.scalar_one_or_none()
        student_name = student.full_name if student else "Неизвестно"
        
        result = await session.execute(
            select(File).where(File.work_id == work_id)
        )
        files = result.scalars().all()
        
        status_info = STATUS_INFO.get(work.status, {"emoji": "❓", "name": work.status})
        
        deadline_str = work.deadline.strftime("%d.%m.%Y") if work.deadline else "Не указан"
        submitted_str = work.submitted_at.strftime("%d.%m.%Y %H:%M") if work.submitted_at else "Не сдана"
        
        files_text = ""
        keyboard_buttons = []
        
        if files:
            files_text = "\n📎 <b>Файлы:</b>\n"
            for i, f in enumerate(files, 1):
                files_text += f"{i}. {f.original_name or f.filename}\n"
                keyboard_buttons.append(
                    InlineKeyboardButton(
                        text=f"⬇️ Скачать файл {i}",
                        callback_data=f"dl:{f.id}"
                    )
                )
        
        # TICKET-3.1: Show grades if they exist
        grade_text = ""
        if work.grade_classic or work.grade_100 or work.grade_letter:
            grade_text = "\n⭐ <b>Оценка:</b>\n"
            if work.grade_classic:
                grade_text += f"   Классическая: {work.grade_classic}\n"
            if work.grade_100:
                grade_text += f"   100-бальная: {work.grade_100}\n"
            if work.grade_letter:
                grade_text += f"   Буквенная: {work.grade_letter}\n"
            if work.is_archived:
                grade_text += "   📁 В архиве\n"
        
        text = f"""{status_info['emoji']} <b>{work.title}</b>
👤 Студент: {student_name}

📊 Статус: {status_info['name']}
📅 Дедлайн: {deadline_str}
📤 Сдана: {submitted_str}

📝 Описание:
{work.description or "Нет описания"}
{files_text}
✍️ Рецензия: {work.teacher_comment or "Не написана"}{grade_text}"""
        
        # Build keyboard
        keyboard_rows = []
        for btn in keyboard_buttons:
            keyboard_rows.append([btn])
        
        # Action buttons - TICKET-3.1: Added grade button
        keyboard_rows.append([
            InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_work:{work.id}"),
            InlineKeyboardButton(text="🔄 На доработку", callback_data=f"revise_work:{work.id}")
        ])
        keyboard_rows.append([
            InlineKeyboardButton(text="🤖 AI-рецензия", callback_data=f"ai_review:{work.id}"),
            InlineKeyboardButton(text="✍️ Рецензия", callback_data=f"add_review:{work.id}"),
        ])
        # TICKET-3.1: Grade button
        keyboard_rows.append([
            InlineKeyboardButton(text="⭐ Оценить", callback_data=f"grade_work:{work.id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"confirm_delete:{work.id}")
        ])
        keyboard_rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback_query.answer()


@router.callback_query(F.data.startswith("dl:"))
async def download_file_handler(callback_query: CallbackQuery):
    """Скачать и отправить файл пользователю"""
    file_id_str = callback_query.data.split(":")[1]
    file_id = uuid.UUID(file_id_str)
    
    await callback_query.answer("⏳ Загружаю...", show_alert=False)
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(File).where(File.id == file_id)
        )
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            await callback_query.answer("❌ Файл не найден", show_alert=True)
            return
        
        # Пробуем найти файл локально
        local_path = None
        if file_record.storage_path and os.path.exists(file_record.storage_path):
            local_path = file_record.storage_path
        else:
            possible_path = f"/app/data/student_files/{file_record.filename}"
            if os.path.exists(possible_path):
                local_path = possible_path
        
        temp_path = None
        try:
            if local_path:
                document = FSInputFile(local_path, filename=file_record.original_name or file_record.filename)
            else:
                from bot.services.minio_service import download_file_to_temp
                temp_path = await download_file_to_temp(file_record.filename)
                if not temp_path:
                    await callback_query.answer("❌ Файл не найден в хранилище", show_alert=True)
                    return
                document = FSInputFile(temp_path, filename=file_record.original_name or file_record.filename)
            
            await callback_query.message.answer_document(
                document=document,
                caption=f"📄 {file_record.original_name or file_record.filename}"
            )
            await callback_query.answer("✅ Готово!")
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await callback_query.answer("❌ Ошибка отправки файла", show_alert=True)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass


@router.callback_query(F.data.startswith("review:"))
async def show_work_review(callback_query: CallbackQuery):
    """Показать рецензию на работу"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await callback_query.answer("Работа не найдена", show_alert=True)
            return
        
        comment_text = work.teacher_comment if work.teacher_comment else "Рецензия еще не написана"
        
        reviewed_at = ""
        if work.teacher_reviewed_at:
            reviewed_at = f"\n🔄 Обновлено: {work.teacher_reviewed_at.strftime('%d.%m.%Y %H:%M')}"
        
        text = f"""✍️ <b>Рецензия на работу: {work.title}</b>

{comment_text}{reviewed_at}"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Изменить рецензию", callback_data=f"add_review:{work.id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("add_review:"))
async def start_add_review(callback_query: CallbackQuery, state):
    """Начать добавление рецензии"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    await state.update_data(review_work_id=work_id_str)
    await state.set_state("waiting_review_text")
    
    await callback_query.message.answer(
        "✍️ <b>Напишите рецензию на работу:</b>\n\n"
        "(ответьте на это сообщение)",
        parse_mode="HTML"
    )
    await callback_query.answer()


@router.callback_query(F.data.startswith("accept_work:"))
async def accept_work(callback_query: CallbackQuery):
    """Принять работу"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            update(StudentWork)
            .where(StudentWork.id == work_id)
            .values(status="accepted")
            .returning(StudentWork)
        )
        work = result.scalar_one_or_none()
        await session.commit()
        
        if work:
            await callback_query.answer("✅ Работа принята!")
            await show_admin_work_details(callback_query)


@router.callback_query(F.data.startswith("revise_work:"))
async def revise_work(callback_query: CallbackQuery):
    """Отправить на доработку"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            update(StudentWork)
            .where(StudentWork.id == work_id)
            .values(status="revision_required")
            .returning(StudentWork)
        )
        work = result.scalar_one_or_none()
        await session.commit()
        
        if work:
            await callback_query.answer("🔄 Отправлена на доработку!")
            await show_admin_work_details(callback_query)


@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_work(callback_query: CallbackQuery):
    """Подтверждение удаления работы"""
    work_id_str = callback_query.data.split(":")[1]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_work:{work_id_str}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_work:{work_id_str}")]
    ])
    
    await callback_query.message.edit_text(
        "🗑️ <b>Удалить работу?</b>\n\n"
        "Это действие нельзя отменить!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()


@router.callback_query(F.data.startswith("delete_work:"))
async def delete_work(callback_query: CallbackQuery):
    """Удалить работу"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            update(StudentWork)
            .where(StudentWork.id == work_id)
            .values(status="rejected")
            .returning(StudentWork)
        )
        work = result.scalar_one_or_none()
        await session.commit()
        
        if work:
            await callback_query.answer("🗑️ Работа удалена!")
            await callback_query.message.edit_text(
                "🗑️ Работа удалена",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👥 К списку студентов", callback_data="back_to_list")]
                ])
            )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback_query: CallbackQuery):
    """Вернуться в главное меню"""
    await callback_query.message.delete()
    await callback_query.answer()
