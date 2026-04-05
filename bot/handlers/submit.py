"""
DigitalTutor Bot - Submit Handler with Local Storage
Файлы сохраняются локально, Яндекс.Диск - опционально
"""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from uuid import uuid4

from bot.config import config
from bot.keyboards import get_main_menu, get_admin_menu, get_work_type_menu, get_cancel_menu, get_yes_no_menu, get_deadline_menu
from bot.templates.messages import Messages
from bot.services.db import AsyncSessionContext
from bot.services.local_file_service import local_file_service
from bot.models import User, StudentWork, WorkType

logger = logging.getLogger(__name__)
router = Router()

class SubmitStates(StatesGroup):
    waiting_type = State()
    waiting_title = State()
    waiting_description = State()
    waiting_deadline = State()
    waiting_file = State()
    waiting_confirm = State()


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(F.text == "➕ Сдать работу")
async def start_submit(message: Message, state: FSMContext):
    """Начало процесса сдачи работы"""
    telegram_id = message.from_user.id
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(Messages.ERROR_REGISTRATION_INCOMPLETE)
            return
        
        await state.update_data(student_id=str(user.id))
    
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
    
    if len(title) < 3:
        await message.answer(
            "❌ Тема слишком короткая. Введите полное название работы.",
            reply_markup=get_cancel_menu()
        )
        return
    
    await state.update_data(title=title)
    await state.set_state(SubmitStates.waiting_description)
    
    await message.answer(
        Messages.SUBMIT_DESCRIPTION,
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания работы"""
    description = message.text.strip()
    
    await state.update_data(description=description)
    await state.set_state(SubmitStates.waiting_deadline)
    
    await message.answer(
        Messages.SUBMIT_DEADLINE,
        reply_markup=get_deadline_menu(),
        parse_mode="HTML"
    )



@router.message(SubmitStates.waiting_deadline, F.text == "⚡ Супер срочно")
async def deadline_urgent(message: Message, state: FSMContext):
    """Супер срочно - завтра"""
    deadline = datetime.utcnow() + timedelta(days=1)
    deadline = deadline.replace(hour=23, minute=59)
    await state.update_data(deadline=deadline)
    await state.set_state(SubmitStates.waiting_file)
    await message.answer(
        "📎 <b>Загрузка файла</b>\n\n"
        "Отправьте файл работы (docx, pdf, txt)\n"
        "Или нажмите /skip чтобы пропустить",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.message(SubmitStates.waiting_deadline, F.text == "🎓 Май")
async def deadline_may(message: Message, state: FSMContext):
    """Дедлайн - конец мая"""
    current_year = datetime.utcnow().year
    deadline = datetime(current_year, 5, 31, 23, 59)
    await state.update_data(deadline=deadline)
    await state.set_state(SubmitStates.waiting_file)
    await message.answer(
        "📎 <b>Загрузка файла</b>\n\n"
        "Отправьте файл работы (docx, pdf, txt)\n"
        "Или нажмите /skip чтобы пропустить",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.message(SubmitStates.waiting_deadline, F.text == "🗓️ Через неделю")
async def deadline_week(message: Message, state: FSMContext):
    """Через неделю"""
    deadline = datetime.utcnow() + timedelta(days=7)
    deadline = deadline.replace(hour=23, minute=59)
    await state.update_data(deadline=deadline)
    await state.set_state(SubmitStates.waiting_file)
    await message.answer(
        "📎 <b>Загрузка файла</b>\n\n"
        "Отправьте файл работы (docx, pdf, txt)\n"
        "Или нажмите /skip чтобы пропустить",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.message(SubmitStates.waiting_deadline, F.text == "📅 Указать дату")
async def deadline_manual(message: Message, state: FSMContext):
    """Пользователь хочет ввести дату вручную"""
    await message.answer(
        "🗓️ <b>Введите дедлайн</b>\n\n"
        "Формат: ДД.ММ.ГГГГ (например, 15.06.2026)",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )

@router.message(SubmitStates.waiting_deadline)
async def process_deadline(message: Message, state: FSMContext):
    """Обработка дедлайна"""
    deadline_text = message.text.strip()
    
    # Парсим дату (формат: ДД.ММ.ГГГГ или ГГГГ-ММ-ДД)
    try:
        if '.' in deadline_text:
            deadline = datetime.strptime(deadline_text, "%d.%m.%Y")
        elif '-' in deadline_text:
            deadline = datetime.strptime(deadline_text, "%Y-%m-%d")
        else:
            raise ValueError
        
        # Устанавливаем время на конец дня
        deadline = deadline.replace(hour=23, minute=59)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 15.06.2026)",
            reply_markup=get_cancel_menu()
        )
        return
    
    await state.update_data(deadline=deadline)
    await state.set_state(SubmitStates.waiting_file)
    
    await message.answer(
        "📎 <b>Загрузка файла</b>\n\n"
        "Отправьте файл работы (docx, pdf, txt)\n"
        "Или нажмите /skip чтобы пропустить",
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(SubmitStates.waiting_file, F.document)
async def process_file(message: Message, state: FSMContext):
    """Обработка загрузки файла - ЛОКАЛЬНОЕ ХРАНЕНИЕ"""
    document = message.document
    
    # Проверяем расширение
    allowed_extensions = ['.docx', '.doc', '.pdf', '.txt', '.odt', '.rtf']
    file_name = document.file_name.lower()
    
    if not any(file_name.endswith(ext) for ext in allowed_extensions):
        await message.answer(
            f"❌ Неподдерживаемый формат файла.\n"
            f"Разрешены: {', '.join(allowed_extensions)}",
            reply_markup=get_cancel_menu()
        )
        return
    
    # Проверяем размер (макс 50 МБ)
    if document.file_size > 50 * 1024 * 1024:
        await message.answer(
            "❌ Файл слишком большой (максимум 50 МБ)",
            reply_markup=get_cancel_menu()
        )
        return
    
    await message.answer("⏳ Загружаю файл...")
    
    try:
        # Скачиваем файл
        file = await message.bot.get_file(document.file_id)
        file_data = await message.bot.download_file(file.file_path)
        
        # Получаем данные из состояния
        data = await state.get_data()
        student_id = data.get('student_id')
        
        # Сохраняем локально
        local_path, file_uuid = local_file_service.save_work_file(
            file_data=file_data.read(),
            original_filename=document.file_name,
            student_id=student_id,
            work_id=str(uuid4())
        )
        
        await state.update_data(
            file_path=local_path,
            file_uuid=file_uuid,
            file_name=document.file_name,
            file_size=document.file_size
        )
        
        await state.set_state(SubmitStates.waiting_confirm)
        
        # Показываем сводку
        await show_summary(message, state)
        
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        await message.answer(
            "❌ Ошибка при сохранении файла. Попробуйте позже.",
            reply_markup=get_main_menu()
        )


@router.message(SubmitStates.waiting_file, F.text == "/skip")
async def skip_file(message: Message, state: FSMContext):
    """Пропуск загрузки файла"""
    await state.update_data(file_path=None, file_name=None)
    await state.set_state(SubmitStates.waiting_confirm)
    await show_summary(message, state)


async def show_summary(message: Message, state: FSMContext):
    """Показать сводку перед сохранением"""
    data = await state.get_data()
    
    text = f"""📋 <b>Проверьте данные:</b>

📚 Тип: {data.get('work_type_name')}
📝 Тема: {data.get('title')}
📄 Описание: {data.get('description', 'нет')[:100]}{'...' if len(data.get('description', '')) > 100 else ''}
📅 Дедлайн: {data.get('deadline').strftime('%d.%m.%Y')}
📎 Файл: {data.get('file_name', 'не загружен')}

✅ Всё верно?"""
    
    await message.answer(text, reply_markup=get_yes_no_menu(), parse_mode="HTML")


@router.message(SubmitStates.waiting_confirm, F.text == "✅ Да")
async def confirm_submit(message: Message, state: FSMContext):
    """Сохранение работы в БД"""
    data = await state.get_data()
    
    try:
        async with AsyncSessionContext() as session:
            # Создаём работу
            work = StudentWork(
                id=uuid4(),
                student_id=data.get('student_id'),
                title=data.get('title'),
                description=data.get('description'),
                deadline=data.get('deadline'),
                status='submitted',
                yandex_file_path=data.get('file_path'),  # Теперь это локальный путь
                submitted_at=datetime.utcnow()
            )
            
            session.add(work)
            await session.commit()
            
            logger.info(f"Work saved: {work.id} for student {data.get('student_id')}")
        
        await message.answer(
            "✅ <b>Работа успешно сохранена!</b>\n\n"
            "Она появится в списке работ и будет проверена.",
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error saving work: {e}")
        await message.answer(
            "❌ Ошибка при сохранении работы. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
    
    await state.clear()


@router.message(SubmitStates.waiting_confirm, F.text == "❌ Нет")
async def cancel_submit(message: Message, state: FSMContext):
    """Отмена сдачи работы"""
    data = await state.get_data()
    
    # Удаляем загруженный файл если есть
    file_path = data.get('file_path')
    if file_path:
        local_file_service.delete_file(file_path)
    
    await state.clear()
    await message.answer(
        "❌ Сдача работы отменена",
        reply_markup=get_main_menu()
    )
