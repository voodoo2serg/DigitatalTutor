"""
DigitalTutor Bot - Student Chat Handler
Полноценный чат админ ↔ студент с историей
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc, or_
from datetime import datetime
from uuid import uuid4

from bot.keyboards import get_admin_menu, get_cancel_menu
from bot.config import config
from bot.models import AsyncSessionContext, User, Communication

logger = logging.getLogger(__name__)
router = Router()

# FSM States для чата
class StudentChatStates(StatesGroup):
    viewing_chat = State()
    composing_message = State()


def format_message_for_history(comm, current_user_id):
    """Форматировать одно сообщение для отображения"""
    time_str = comm.created_at.strftime("%d.%m %H:%M")
    
    # Определяем направление
    if comm.from_teacher and not comm.from_student:
        sender = "Вы"
        direction = "→"
    elif comm.from_student and not comm.from_teacher:
        sender = "Студент"
        direction = "←"
    else:
        sender = "?"
        direction = "—"
    
    # Определяем тип
    if comm.message_type == 'mass':
        type_label = "[📢 МАССОВАЯ]"
    elif comm.message_type == 'personal':
        type_label = "[💬 ЛИЧНОЕ]"
    elif comm.message_type == 'review':
        type_label = "[📝 РЕЦЕНЗИЯ]"
    else:
        type_label = ""
    
    text = f"<b>{time_str}</b> {sender} {direction} {type_label}\n"
    text += f"{comm.content[:300]}"
    if len(comm.content) > 300:
        text += "..."
    
    return text


@router.callback_query(F.data.startswith("view_chat:"))
async def view_student_chat(callback: CallbackQuery, state: FSMContext):
    """Просмотр истории сообщений со студентом"""
    student_id = callback.data.split(":")[1]
    
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    async with AsyncSessionContext() as session:
        # Получаем данные студента
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return
        
        # Получаем все сообщения со студентом
        # Включаем: личные от админа, ответы от студента, массовые
        result = await session.execute(
            select(Communication).where(
                or_(
                    Communication.from_user_id == student_id,
                    Communication.to_user_id == student_id,
                    and_(
                        Communication.from_teacher == True,
                        Communication.content.contains(student.full_name[:20]) if student.full_name else False
                    )
                )
            ).order_by(desc(Communication.created_at)).limit(50)
        )
        messages = result.scalars().all()
        
        # Формируем текст
        text = f"💬 <b>История сообщений с {student.full_name}</b>\n"
        text += f"📱 Telegram: {student.telegram_username or 'не указан'}\n"
        text += f"🆔 ID: <code>{student.telegram_id}</code>\n"
        text += "━" * 30 + "\n\n"
        
        if not messages:
            text += "<i>Пока нет сообщений...</i>"
        else:
            # Показываем в обратном порядке (новые снизу)
            for comm in reversed(messages):
                text += format_message_for_history(comm, callback.from_user.id) + "\n\n"
        
        # Кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_to:{student_id}")],
            [InlineKeyboardButton(text="📤 Массовая рассылка", callback_data="start_mass_messaging")],
            [InlineKeyboardButton(text="✉️ Открыть в Telegram", url=f"tg://user?id={student.telegram_id}")],
            [InlineKeyboardButton(text="« Назад к списку", callback_data="back_to_students")]
        ])
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except TelegramBadRequest as e:
            if "BUTTON_USER_INVALID" in str(e):
                safe = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_to:{student_id}")],
                    [InlineKeyboardButton(text="📤 Массовая рассылка", callback_data="start_mass_messaging")],
                    [InlineKeyboardButton(text="« Назад к списку", callback_data="back_to_students")]
                ])
                await callback.message.edit_text(text, reply_markup=safe, parse_mode="HTML")
            else:
                raise
        await callback.answer()


@router.callback_query(F.data.startswith("reply_to:"))
async def start_reply_to_student(callback: CallbackQuery, state: FSMContext):
    """Начать ответ студенту (из истории)"""
    student_id = callback.data.split(":")[1]
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return
        
        # Сохраняем контекст
        await state.update_data(
            chat_student_id=student_id,
            chat_student_name=student.full_name,
            chat_student_tg_id=student.telegram_id
        )
        await state.set_state(StudentChatStates.composing_message)
        
        text = f"💬 <b>Написать {student.full_name}</b>\n\n"
        text += "Введите сообщение:\n"
        text += "<i>Оно будет отправлено студенту и сохранено в истории.</i>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Отмена", callback_data=f"view_chat:{student_id}")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.message(StudentChatStates.composing_message)
async def send_personal_message(message: Message, state: FSMContext):
    """Отправить личное сообщение студенту"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=get_admin_menu())
        return
    
    data = await state.get_data()
    student_id = data.get('chat_student_id')
    student_name = data.get('chat_student_name')
    student_tg_id = data.get('chat_student_tg_id')
    
    if not student_id:
        await message.answer("Ошибка: студент не найден", reply_markup=get_admin_menu())
        await state.clear()
        return
    
    msg_text = message.text
    
    try:
        async with AsyncSessionContext() as session:
            # Получаем ID админа
            admin_result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            admin = admin_result.scalar_one_or_none()
            admin_id = admin.id if admin else None
            
            # Создаём запись в БД
            comm = Communication(
                id=uuid4(),
                from_user_id=admin_id,
                to_user_id=student_id,
                channel="telegram",
                message_type="personal",
                message=msg_text,
                content=msg_text,
                from_student=False,
                from_teacher=True,
                is_read=False,
                created_at=datetime.utcnow()
            )
            session.add(comm)
            await session.commit()
            
            # Отправляем студенту
            try:
                await message.bot.send_message(
                    chat_id=student_tg_id,
                    text=f"💬 <b>Сообщение от руководителя:</b>\n\n{msg_text}",
                    parse_mode="HTML"
                )
                
                await message.answer(
                    f"✅ Сообщение отправлено {student_name}!",
                    reply_markup=get_admin_menu()
                )
            except Exception as e:
                logger.error(f"Failed to send to student: {e}")
                await message.answer(
                    f"⚠️ Сообщение сохранено, но не удалось отправить студенту.\n"
                    f"Возможно, он заблокировал бота.",
                    reply_markup=get_admin_menu()
                )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error sending personal message: {e}")
        await message.answer(
            "❌ Ошибка при отправке сообщения",
            reply_markup=get_admin_menu()
        )
        await state.clear()
