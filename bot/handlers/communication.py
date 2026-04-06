"""
DigitalTutor Bot - Communication Handler
Написать руководителю
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from datetime import datetime
from uuid import uuid4

from bot.keyboards import get_main_menu, get_cancel_menu
from bot.templates.messages import Messages

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = [502621151]

# FSM States
class CommunicationStates(StatesGroup):
    waiting_message = State()


@router.message(F.text == "💬 Написать руководителю")
async def start_communication(message: Message, state: FSMContext):
    """Начать общение с руководителем"""
    telegram_id = message.from_user.id
    
    from bot.models import AsyncSessionContext, User
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(Messages.ERROR_REGISTRATION_INCOMPLETE)
            return
        
        await state.update_data(student_id=str(user.id))
    
    await state.set_state(CommunicationStates.waiting_message)
    await message.answer(
        Messages.COMMUNICATION_START,
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(CommunicationStates.waiting_message)
async def process_message(message: Message, state: FSMContext):
    """Обработка сообщения для руководителя"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            Messages.CONFIRM_CANCEL,
            reply_markup=get_main_menu()
        )
        return
    
    msg_text = message.text or "[Медиа-сообщение]"
    
    if len(msg_text) < 3:
        await message.answer(
            "❌ Сообщение слишком короткое. Опишите ваш вопрос подробнее.",
            reply_markup=get_cancel_menu()
        )
        return
    
    data = await state.get_data()
    student_id = data.get("student_id")
    
    try:
        from bot.models import AsyncSessionContext, Communication
        
        async with AsyncSessionContext() as session:
            comm = Communication(
                id=uuid4(),
                from_user_id=student_id,
                to_user_id=None,
                channel="telegram",
                message_type="text",
                message=msg_text,
                content=msg_text,
                from_student=True,
                from_teacher=False,
                is_read=False,
                created_at=datetime.utcnow()
            )
            session.add(comm)
            await session.commit()
        
        # Уведомляем админов
        try:
            for admin_id in ADMIN_IDS:
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=f"📩 <b>Новое сообщение от студента</b>\n\n"
                         f"👤 Студент: {message.from_user.full_name}\n"
                         f"💬 Сообщение:\n{msg_text[:500]}",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        await message.answer(
            Messages.COMMUNICATION_SENT,
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Communication error: {e}")
        await message.answer(
            "❌ Ошибка при отправке сообщения. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await state.clear()
