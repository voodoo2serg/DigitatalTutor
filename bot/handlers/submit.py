"""
DigitalTutor Bot - Submit Handler
Сдача работы (Conversation Handler)
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from uuid import uuid4

from bot.keyboards import (
    get_main_menu, get_cancel_menu, get_work_type_menu,
    get_deadline_menu, get_yes_no_menu
)
from bot.templates.messages import Messages
from bot.services.yandex_service import YandexDiskService

logger = logging.getLogger(__name__)
router = Router()

# FSM States для сдачи работы
class SubmitStates(StatesGroup):
    waiting_type = State()
    waiting_title = State()
    waiting_deadline_choice = State()
    waiting_deadline_date = State()
    waiting_file = State()
    confirm = State()


@router.message(F.text == "➕ Сдать работу")
async def start_submit(message: Message, state: FSMContext):
    """Начать процесс сдачи работы"""
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
        
        await state.update_data(student_id=str(user.id), yandex_folder=user.yandex_folder)
    
    await state.set_state(SubmitStates.waiting_type)
    await message.answer(
        Messages.SUBMIT_START,
        reply_markup=get_work_type_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_type)
async def process_work_type(message: Message, state: FSMContext):
    """Обработка типа работы"""
    type_mapping = {
        "📚 Курсовая работа": ("Курсовая работа", "coursework"),
        "🎓 ВКР (Бакалавр)": ("ВКР (Бакалавр)", "vkr_bachelor"),
        "🎓 ВКР (Магистр)": ("ВКР (Магистр)", "vkr_master"),
        "📄 Научная статья": ("Научная статья", "article"),
        "📝 Реферат": ("Реферат", "essay"),
        "🔧 Проект": ("Проект", "project"),
        "❓ Другое": ("Другое", "other"),
    }
    
    work_type_text = message.text
    work_type_info = type_mapping.get(work_type_text)
    
    if not work_type_info:
        await message.answer(
            "❌ Пожалуйста, выберите тип работы из списка",
            reply_markup=get_work_type_menu()
        )
        return
    
    await state.update_data(
        work_type_name=work_type_info[0],
        work_type_code=work_type_info[1]
    )
    await state.set_state(SubmitStates.waiting_title)
    
    await message.answer(
        Messages.SUBMIT_TITLE.format(work_type=work_type_info[0]),
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_title)
async def process_title(message: Message, state: FSMContext):
    """Обработка темы работы"""
    title = message.text.strip()
    
    if len(title) < 5:
        await message.answer(
            "❌ Название слишком короткое (минимум 5 символов)",
            reply_markup=get_cancel_menu()
        )
        return
    
    await state.update_data(title=title)
    await state.set_state(SubmitStates.waiting_deadline_choice)
    
    await message.answer(
        Messages.SUBMIT_DEADLINE.format(title=title),
        reply_markup=get_deadline_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_deadline_choice)
async def process_deadline_choice(message: Message, state: FSMContext):
    """Обработка выбора дедлайна"""
    choice = message.text
    
    if choice == "⚡ Супер срочно":
        deadline = datetime.utcnow() + timedelta(days=1)
        await state.update_data(deadline=deadline, deadline_str="Супер срочно (завтра)")
        await ask_for_file(message, state)
        
    elif choice == "🎓 Май":
        now = datetime.utcnow()
        deadline = datetime(now.year, 5, 31, 23, 59, 59)
        if now.month > 5:
            deadline = datetime(now.year + 1, 5, 31, 23, 59, 59)
        await state.update_data(deadline=deadline, deadline_str=f"Май {deadline.year}")
        await ask_for_file(message, state)
        
    elif choice == "🗓️ Через неделю":
        deadline = datetime.utcnow() + timedelta(days=7)
        await state.update_data(deadline=deadline, deadline_str="Через неделю")
        await ask_for_file(message, state)
        
    elif choice == "📅 Указать дату":
        await state.set_state(SubmitStates.waiting_deadline_date)
        await message.answer(
            Messages.SUBMIT_DATE_MANUAL,
            reply_markup=get_cancel_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Пожалуйста, выберите вариант из списка",
            reply_markup=get_deadline_menu()
        )


@router.message(SubmitStates.waiting_deadline_date)
async def process_manual_date(message: Message, state: FSMContext):
    """Обработка ввода даты вручную"""
    date_text = message.text.strip()
    
    try:
        day, month, year = map(int, date_text.split("."))
        deadline = datetime(year, month, day, 23, 59, 59)
        
        if deadline < datetime.utcnow():
            await message.answer(
                "❌ Дата не может быть в прошлом. Попробуйте ещё раз.",
                reply_markup=get_cancel_menu()
            )
            return
        
        await state.update_data(deadline=deadline, deadline_str=date_text)
        await ask_for_file(message, state)
        
    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверный формат. Используйте формат ДД.ММ.ГГГГ",
            reply_markup=get_cancel_menu()
        )


async def ask_for_file(message: Message, state: FSMContext):
    """Запросить файл"""
    await state.set_state(SubmitStates.waiting_file)
    
    data = await state.get_data()
    deadline_str = data.get("deadline_str", "Не указан")
    
    await message.answer(
        Messages.SUBMIT_FILE.format(deadline=deadline_str),
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_file, F.document)
async def process_file(message: Message, state: FSMContext):
    """Обработка загруженного файла"""
    document = message.document
    
    if document.file_size > 20 * 1024 * 1024:
        await message.answer(Messages.ERROR_FILE_TOO_LARGE, reply_markup=get_cancel_menu())
        return
    
    allowed_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ]
    
    if document.mime_type not in allowed_types:
        await message.answer(Messages.ERROR_FILE_TYPE, reply_markup=get_cancel_menu())
        return
    
    try:
        file_obj = await message.bot.get_file(document.file_id)
        file_bytes = await message.bot.download_file(file_obj.file_path)
        file_content = file_bytes.read()
        
        await state.update_data(
            file_content=file_content,
            filename=document.file_name,
            mime_type=document.mime_type
        )
        
        await show_confirmation(message, state)
        
    except Exception as e:
        logger.error(f"File download error: {e}")
        await message.answer(
            "❌ Ошибка при загрузке файла. Попробуйте ещё раз.",
            reply_markup=get_cancel_menu()
        )


@router.message(SubmitStates.waiting_file, F.text == "/skip")
async def skip_file(message: Message, state: FSMContext):
    """Пропустить загрузку файла"""
    await state.update_data(file_content=None, filename=None, mime_type=None)
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Показать подтверждение"""
    data = await state.get_data()
    
    work_type = data.get("work_type_name")
    title = data.get("title")
    deadline_str = data.get("deadline_str", "Не указан")
    filename = data.get("filename", "Без файла")
    
    await state.set_state(SubmitStates.confirm)
    
    await message.answer(
        Messages.SUBMIT_CONFIRM.format(
            work_type=work_type,
            title=title,
            deadline=deadline_str,
            filename=filename
        ),
        reply_markup=get_yes_no_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.confirm, F.text == "✅ Да")
async def confirm_submission(message: Message, state: FSMContext):
    """Подтверждение и сохранение работы"""
    data = await state.get_data()
    
    student_id = data.get("student_id")
    yandex_folder = data.get("yandex_folder")
    title = data.get("title")
    deadline = data.get("deadline")
    file_content = data.get("file_content")
    filename = data.get("filename")
    work_type_code = data.get("work_type_code")
    work_type_name = data.get("work_type_name")
    
    await message.answer("🔄 Сохраняю работу...")
    
    try:
        from bot.models import AsyncSessionContext, StudentWork, File, WorkType
        import os
        
        async with AsyncSessionContext() as session:
            result = await session.execute(
                select(WorkType).where(WorkType.code == work_type_code)
            )
            work_type = result.scalar_one_or_none()
            
            if not work_type:
                work_type = WorkType(
                    id=uuid4(),
                    code=work_type_code,
                    name=work_type_name
                )
                session.add(work_type)
                await session.flush()
            
            work_id = uuid4()
            work = StudentWork(
                id=work_id,
                student_id=student_id,
                work_type_id=work_type.id,
                title=title,
                status="submitted",
                deadline=deadline,
                submitted_at=datetime.utcnow()
            )
            session.add(work)
            
            if file_content and filename:
                yandex_token = os.getenv("YANDEX_DISK_TOKEN", "")
                yandex = YandexDiskService(yandex_token)
                yandex_path = await yandex.upload_student_file(
                    file_data=file_content,
                    filename=filename,
                    student_folder=yandex_folder,
                    work_id=str(work_id)
                )
                
                file_record = File(
                    id=uuid4(),
                    work_id=work_id,
                    filename=filename,
                    original_name=filename,
                    mime_type=data.get("mime_type", "application/octet-stream"),
                    size_bytes=len(file_content),
                    storage_type="yandex",
                    yandex_file_path=yandex_path
                )
                session.add(file_record)
        
        await message.answer(
            Messages.SUBMIT_SUCCESS.format(
                title=title,
                deadline=data.get("deadline_str", "Не указан")
            ),
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Submit error: {e}")
        await message.answer(
            "❌ Ошибка при сохранении работы. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await state.clear()


@router.message(SubmitStates.confirm, F.text == "❌ Нет")
async def cancel_submit(message: Message, state: FSMContext):
    """Отмена сдачи работы"""
    await state.clear()
    await message.answer(
        Messages.CONFIRM_CANCEL,
        reply_markup=get_main_menu()
    )
