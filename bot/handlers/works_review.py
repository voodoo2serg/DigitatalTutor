"""
DigitalTutor Bot - Review Handler (Add/Edit + Reply to file)
"""
import logging
import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from sqlalchemy import select, update

from bot.models import AsyncSessionContext, StudentWork
from bot.keyboards import get_main_menu, get_admin_menu

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = [502621151]

class ReviewStates(StatesGroup):
    waiting_for_review = State()


@router.callback_query(F.data.startswith("add_review:"))
async def start_add_review(callback_query: CallbackQuery, state: FSMContext):
    """Начать добавление рецензии"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    await state.update_data(work_id=work_id_str)
    await state.set_state(ReviewStates.waiting_for_review)
    
    await callback_query.message.edit_text(
        "✍️ <b>Добавление рецензии</b>\n\n"
        "Введите текст рецензии:",
        parse_mode="HTML"
    )
    await callback_query.answer()


@router.message(ReviewStates.waiting_for_review)
async def process_review(message: Message, state: FSMContext):
    """Обработать ввод рецензии"""
    data = await state.get_data()
    work_id_str = data.get("work_id")
    
    if not work_id_str:
        await message.answer("Ошибка: ID работы не найден", reply_markup=get_admin_menu())
        await state.clear()
        return
    
    work_id = uuid.UUID(work_id_str)
    review_text = message.text
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await message.answer("Работа не найдена", reply_markup=get_admin_menu())
            await state.clear()
            return
        
        work.teacher_comment = review_text
        work.teacher_reviewed_at = datetime.utcnow()
        await session.commit()
        
        await message.answer(
            f"✅ <b>Рецензия сохранена!</b>\n\n"
            f"Работа: {work.title[:50]}...",
            reply_markup=get_admin_menu(),
            parse_mode="HTML"
        )
    
    await state.clear()


@router.message(F.reply_to_message)
async def handle_reply_as_review(message: Message):
    """
    Handle admin reply to work details message as review.
    If admin replies to a message containing work details, save reply as review.
    """
    # Check if user is admin
    if message.from_user.id not in ADMIN_IDS:
        return
    
    # Check if replying to bot's message
    if not message.reply_to_message.from_user.is_bot:
        return
    
    # Import work_messages_map from works module
    from bot.handlers.works import get_work_messages_map
    work_messages_map = get_work_messages_map()
    
    # Check if this message is tracked as a work details message
    original_msg_id = message.reply_to_message.message_id
    work_id = work_messages_map.get(original_msg_id)
    
    if not work_id:
        # Try to extract work_id from message text (fallback)
        text = message.reply_to_message.text or ""
        if "Работа удалена" in text or "Подтвердите удаление" in text:
            return
        # Not a work message, ignore
        return
    
    # Get review text from reply
    review_text = message.text or message.caption or ""
    
    if not review_text.strip():
        await message.answer("❌ Рецензия не может быть пустой")
        return
    
    # Save review to database
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await message.answer("❌ Работа не найдена")
            return
        
        # Update work with review
        await session.execute(
            update(StudentWork)
            .where(StudentWork.id == work_id)
            .values(
                teacher_comment=review_text,
                teacher_reviewed_at=datetime.utcnow(),
                status="in_review" if work.status == "submitted" else work.status
            )
        )
        await session.commit()
        
        logger.info(f"Review added to work {work_id} by admin {message.from_user.id}")
    
    # Confirm to admin
    await message.answer(
        f"✅ <b>Рецензия сохранена!</b>\n\n"
        f"Работа: {work.title}\n"
        f"Текст рецензии:\n{review_text[:200]}{'...' if len(review_text) > 200 else ''}",
        parse_mode="HTML"
    )
