"""
DigitalTutor Bot - Registration Handler
Регистрация студентов с ролью
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func
from uuid import uuid4

from bot.keyboards import get_main_menu, get_role_selection_menu, get_cancel_menu
from bot.templates.messages import Messages
from bot.services.yandex_service import yandex_service
from bot.config import config

logger = logging.getLogger(__name__)
router = Router()

# FSM States для регистрации
class RegistrationStates(StatesGroup):
    waiting_fio = State()
    waiting_group = State()
    waiting_course = State()
    waiting_role = State()


async def start_registration(message: Message):
    """Начать процесс регистрации"""
    from bot.models import AsyncSessionContext, User
    
    telegram_id = message.from_user.id
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await message.answer(
                "Вы уже зарегистрированы!",
                reply_markup=get_main_menu()
            )
            return
    
    await message.answer(
        Messages.WELCOME_NEW,
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )
    await message.answer(
        Messages.REGISTRATION_START,
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "❌ Отмена")
async def cancel_registration(message: Message, state: FSMContext):
    """Отмена регистрации"""
    await state.clear()
    await message.answer(
        Messages.CONFIRM_CANCEL,
        reply_markup=get_main_menu()
    )


@router.message(RegistrationStates.waiting_fio)
async def process_fio(message: Message, state: FSMContext):
    """Обработка ФИО"""
    fio = message.text.strip()
    
    if len(fio.split()) < 2:
        await message.answer(
            "❌ Пожалуйста, введите полное ФИО (фамилия имя отчество)",
            reply_markup=get_cancel_menu()
        )
        return

    # Проверка на дубликаты по ФИО
    async with AsyncSessionContext() as session:
        surname = fio.split()[0].lower()
        result = await session.execute(
            select(User).where(func.lower(User.full_name).like(f"%{surname}%"))
        )
        similar = result.scalars().all()
        if similar:
            await message.answer(
                f"⚠️ В системе есть похожие имена: {', '.join([u.full_name for u in similar[:3]])}",
                reply_markup=get_yes_no_menu()
            )
            return
    
    await state.update_data(fio=fio)
    await state.set_state(RegistrationStates.waiting_group)
    
    await message.answer(
        Messages.REGISTRATION_GROUP.format(fio=fio),
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.waiting_group)
async def process_group(message: Message, state: FSMContext):
    """Обработка группы"""
    group = message.text.strip()
    
    if len(group) < 2:
        await message.answer(
            "❌ Номер группы слишком короткий. Попробуйте ещё раз.",
            reply_markup=get_cancel_menu()
        )
        return
    
    await state.update_data(group=group)
    await state.set_state(RegistrationStates.waiting_course)
    
    await message.answer(
        Messages.REGISTRATION_COURSE.format(group=group),
        reply_markup=get_cancel_menu(),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.waiting_course)
async def process_course(message: Message, state: FSMContext):
    """Обработка курса"""
    course_text = message.text.strip()
    
    try:
        course = int(course_text)
        if course < 1 or course > 6:
            raise ValueError()
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите число от 1 до 6",
            reply_markup=get_cancel_menu()
        )
        return
    
    await state.update_data(course=course)
    await state.set_state(RegistrationStates.waiting_role)
    
    await message.answer(
        Messages.REGISTRATION_ROLE.format(course=course),
        reply_markup=get_role_selection_menu(),
        parse_mode="HTML"
    )


@router.message(RegistrationStates.waiting_role)
async def process_role(message: Message, state: FSMContext):
    """Обработка выбора роли"""
    role_mapping = {
        "🎓 ВКР": ("vkr", "ВКР"),
        "🔬 Аспирант": ("aspirant", "Аспирант"),
        "📝 ВКР + Статья": ("vkr_article", "ВКР + Статья"),
        "📄 Руководство по статье": ("article_guide", "Руководство по статье"),
        "📚 Руководство по работе": ("work_guide", "Руководство по работе"),
        "🔧 Другой проект": ("other", "Другой проект"),
    }
    
    role_text = message.text
    role_info = role_mapping.get(role_text)
    
    if not role_info:
        await message.answer(
            "❌ Пожалуйста, выберите роль из списка",
            reply_markup=get_role_selection_menu()
        )
        return
    
    role_code, role_name = role_info
    await state.update_data(role=role_code, role_name=role_name)
    
    await complete_registration(message, state)


async def complete_registration(message: Message, state: FSMContext):
    """Завершение регистрации"""
    data = await state.get_data()
    
    fio = data.get("fio")
    group = data.get("group")
    course = data.get("course")
    role_code = data.get("role")
    role_name = data.get("role_name")
    
    telegram_id = message.from_user.id
    username = message.from_user.username
    
    try:
        # Use global yandex_service instance and correct method signature
        folder_path = yandex_service.create_student_folder(
            role=role_code,
            student_name=fio,
            group_name=group
        )
        
        from bot.models import AsyncSessionContext, User
        
        async with AsyncSessionContext() as session:
            user = User(
                id=uuid4(),
                telegram_id=telegram_id,
                telegram_username=username,
                full_name=fio,
                role=role_name,
                group_name=group,
                course=course,
                yandex_folder=folder_path,
                is_active=True
            )
            session.add(user)
        
        STUDENT_ROLES = {
            "vkr": {"name": "ВКР", "plan_points": [{"num": 1, "name": "Предзащита"}, {"num": 2, "name": "Финальная защита"}]},
            "aspirant": {"name": "Аспирант", "plan_points": [{"num": i, "name": f"Этап {i}"} for i in range(1, 7)]},
            "vkr_article": {"name": "ВКР + Статья", "plan_points": [{"num": i, "name": f"Этап {i}"} for i in range(1, 4)]},
            "article_guide": {"name": "Руководство по статье", "plan_points": [{"num": i, "name": f"Этап {i}"} for i in range(1, 4)]},
            "work_guide": {"name": "Руководство по работе", "plan_points": [{"num": i, "name": f"Этап {i}"} for i in range(1, 4)]},
            "other": {"name": "Другой проект", "plan_points": [{"num": i, "name": f"Этап {i}"} for i in range(1, 4)]},
        }
        
        role_info = STUDENT_ROLES.get(role_code, {})
        plan_points = role_info.get("plan_points", [])
        plan_text = "\n".join([f"{p['num']}. {p['name']}" for p in plan_points])
        
        await message.answer(
            Messages.REGISTRATION_COMPLETE.format(
                fio=fio,
                group=group,
                course=course,
                role=role_name,
                plan_text=f"📋 <b>Ваш план работ:</b>\n{plan_text}"
            ),
            reply_markup=get_main_menu(),
            parse_mode="HTML"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        await message.answer(
            "❌ Ошибка при регистрации. Попробуйте позже или обратитесь к администратору.",
            reply_markup=get_cancel_menu()
        )
