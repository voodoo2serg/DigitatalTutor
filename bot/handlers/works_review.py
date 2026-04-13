"""
DigitalTutor Bot - Works Review Handler
Детальный просмотр и рецензирование работ
"""
import logging
import uuid
from aiogram import Router, F
from aiogram.filters.state import StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update

from bot.config import config
from bot.keyboards import get_admin_menu

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("add_review:"))
async def start_add_review(callback: CallbackQuery, state: FSMContext):
    """Начать написание рецензии"""
    work_id_str = callback.data.split(":")[1]

    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ У вас нет доступа.", show_alert=True)
        return

    await state.update_data(review_work_id=work_id_str)
    await state.set_state("waiting_review_text")

    # Show work info for context
    from bot.models import AsyncSessionContext, StudentWork, User

    async with AsyncSessionContext() as session:
        work = await session.execute(
            select(StudentWork).where(StudentWork.id == uuid.UUID(work_id_str))
        )
        work = work.scalar_one_or_none()

        if work:
            student_result = await session.execute(select(User).where(User.id == work.student_id))
            student = student_result.scalar_one_or_none()
            student_name = student.full_name if student else "Студент"

            # Show existing scores
            score_text = ""
            if work.ai_plagiarism_score:
                score_text += f"\n📊 Оригинальность: {work.ai_plagiarism_score}/100"
            if work.ai_structure_score:
                score_text += f"\n🏗️ Структура: {work.ai_structure_score}/100"
            if work.ai_formatting_score:
                score_text += f"\n📝 Оформление: {work.ai_formatting_score}/100"

            await callback.message.answer(
                f"✍️ <b>Рецензия на работу</b>\n\n"
                f"📝 {work.title}\n"
                f"👤 {student_name}{score_text}\n\n"
                f"Напишите текст рецензии (ответьте на это сообщение):\n",
                parse_mode="HTML"
            )

    await callback.answer()


@router.message(F.text == "❌ Отмена рецензии")
async def cancel_review(message: Message, state: FSMContext):
    """Отмена написания рецензии"""
    await state.clear()
    await message.answer("❌ Рецензия отменена", reply_markup=get_admin_menu())


# Register review text handler
review_router = Router()


@review_router.message(F.text, StateFilter("waiting_review_text"))
async def save_review(message: Message, state: FSMContext):
    """Сохранить рецензию"""
    review_text = message.text.strip()

    if not review_text:
        await message.answer("❌ Рецензия не может быть пустой")
        return

    data = await state.get_data()
    work_id_str = data.get("review_work_id")

    if not work_id_str:
        await state.clear()
        return

    try:
        from bot.models import AsyncSessionContext, StudentWork, User
        from datetime import datetime

        async with AsyncSessionContext() as session:
            work_id = uuid.UUID(work_id_str)

            await session.execute(
                update(StudentWork)
                .where(StudentWork.id == work_id)
                .values(
                    teacher_comment=review_text,
                    teacher_reviewed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )

            # Notify student
            work_result = await session.execute(select(StudentWork).where(StudentWork.id == work_id))
            work = work_result.scalar_one_or_none()

            if work and work.student_id:
                student_result = await session.execute(select(User).where(User.id == work.student_id))
                student = student_result.scalar_one_or_none()

                if student and student.telegram_id:
                    try:
                        await message.bot.send_message(
                            chat_id=student.telegram_id,
                            text=(
                                f"✍️ <b>Новая рецензия на вашу работу</b>\n\n"
                                f"📝 {work.title}\n\n"
                                f"{review_text[:500]}"
                                f"{'...' if len(review_text) > 500 else ''}\n\n"
                                f"Подробности в разделе «📋 Мои работы»"
                            ),
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify student: {e}")

        await message.answer(
            "✅ Рецензия сохранена!\n\n"
            f"Текст рецензии:\n{review_text[:200]}"
            f"{'...' if len(review_text) > 200 else ''}",
            reply_markup=get_admin_menu()
        )

        await state.clear()

    except Exception as e:
        logger.error(f"Failed to save review: {e}")
        await message.answer(f"❌ Ошибка сохранения рецензии: {e}")
