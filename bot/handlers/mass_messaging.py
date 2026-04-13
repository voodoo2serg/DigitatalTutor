"""
DigitalTutor Bot - Mass Messaging Handler
Массовые рассылки для администратора
"""
import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, 
    FSInputFile, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os

from bot.keyboards import get_admin_menu, get_cancel_menu
from bot.config import config
from bot.models import AsyncSessionContext, User, StudentWork, WebAuthCode

logger = logging.getLogger(__name__)
router = Router()

# FSM States для массовой рассылки
class MassMessagingStates(StatesGroup):
    selecting_students = State()
    composing_message = State()
    setting_throttling = State()
    setting_deadline = State()
    confirming_send = State()
    waiting_for_file = State()

# FSM States для генерации ключей веб-доступа
class WebAuthStates(StatesGroup):
    selecting_student_for_auth = State()
    confirming_key_generation = State()

# Хранение данных рассылки (временно, для FSM)
# В продакшене лучше использовать Redis или базу данных

# Настройка throttling (в секундах) - берётся из config или 15 по умолчанию
DEFAULT_THROTTLING = config.THROTTLING_DELAY

# Типы работ для фильтрации
WORK_TYPE_FILTERS = {
    "all": "Все типы",
    "vkr": "🎓 ВКР",
    "article": "📄 Статья",
    "essay": "📝 Реферат",
    "project": "🔧 Проект",
    "coursework": "📚 Курсовая",
}

# Маппинг типов работ
WORK_TYPE_MAPPING = {
    "ВКР (Бакалавр)": "vkr",
    "ВКР (Магистр)": "vkr",
    "Научная статья": "article",
    "Реферат": "essay",
    "Проект": "project",
    "Курсовая работа": "coursework",
}


def get_work_type_emoji(work_type: str) -> str:
    """Получить эмодзи для типа работы"""
    emoji_map = {
        "Курсовая работа": "📚",
        "ВКР (Бакалавр)": "🎓",
        "ВКР (Магистр)": "🎓",
        "Научная статья": "📄",
        "Реферат": "📝",
        "Проект": "🔧",
    }
    return emoji_map.get(work_type, "📋")


def get_student_status_color(works: List[StudentWork]) -> str:
    """
    Определить цвет статуса студента:
    🔴 - есть просроченные работы ИЛИ >3 дней без ответа
    🟡 - дедлайн ≤3 дня ИЛИ 1-3 дня без ответа
    🟢 - всё в порядке
    """
    if not works:
        return "⚪"
    
    now = datetime.utcnow()
    has_overdue = False
    has_soon = False
    
    for work in works:
        if work.deadline:
            days_left = (work.deadline - now).days
            if days_left < 0:
                has_overdue = True
            elif days_left <= 3:
                has_soon = True
    
    if has_overdue:
        return "🔴"
    elif has_soon:
        return "🟡"
    else:
        return "🟢"


def get_latest_work_info(works: List[StudentWork]) -> tuple:
    """Получить информацию о последней актуальной работе"""
    if not works:
        return "⚪", "нет работ", None
    
    # Сортируем по дате создания (самая новая)
    latest_work = max(works, key=lambda w: w.created_at)
    
    STATUS_MAP = {
        "draft": "черновик",
        "submitted": "отправлена",
        "in_review": "на проверке",
        "revision_required": "доработка",
        "accepted": "завершена",
        "rejected": "отклонена",
    }
    
    # Определяем цвет работы
    now = datetime.utcnow()
    if latest_work.deadline and latest_work.deadline < now:
        work_color = "🔴"
    elif latest_work.status == "accepted":
        work_color = "🟢"
    elif latest_work.status in ["submitted", "in_review"]:
        work_color = "🟡"
    else:
        work_color = "🔴"
    
    status_text = STATUS_MAP.get(latest_work.status, latest_work.status)
    work_type = latest_work.work_type or "работа"
    
    return work_color, f"{work_type} ({status_text})", latest_work.id


def filter_students_by_work_type(students_data: List[Dict], works_data: Dict, filter_type: str) -> List[Dict]:
    """Фильтровать студентов по типу работы"""
    if filter_type == "all":
        return students_data
    
    filtered = []
    for student in students_data:
        student_id = student['id']
        works = works_data.get(student_id, [])
        
        # Проверяем, есть ли у студента работа нужного типа
        has_matching_work = False
        for work in works:
            work_type_key = WORK_TYPE_MAPPING.get(work.work_type, "")
            if work_type_key == filter_type:
                has_matching_work = True
                break
        
        if has_matching_work:
            filtered.append(student)
    
    return filtered


@router.message(F.text == "📤 Массовая рассылка")
async def start_mass_messaging(message: Message, state: FSMContext):
    """Начать массовую рассылку - шаг 1: выбор студентов с фильтрами"""
    telegram_id = message.from_user.id
    
    if telegram_id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой функции.")
        return
    
    async with AsyncSessionContext() as session:
        # Получаем всех студентов (role = 'student' или 'aspirant')
        result = await session.execute(
            select(User).where(
                User.role.in_(['student', 'aspirant'])
            ).order_by(User.full_name)
        )
        students = result.scalars().all()
        
        if not students:
            await message.answer("❌ Нет зарегистрированных студентов.")
            return
        
        # Получаем работы для всех студентов
        students_data = []
        works_data = {}
        
        for student in students:
            result = await session.execute(
                select(StudentWork).where(StudentWork.student_id == student.id)
            )
            works = result.scalars().all()
            works_data[str(student.id)] = works
            
            color, work_status, _ = get_latest_work_info(works)
            
            students_data.append({
                'id': str(student.id),
                'telegram_id': student.telegram_id,
                'name': student.full_name or f"User_{student.telegram_id}",
                'color': color,
                'work_status': work_status,
                'group': student.group_name or "—"
            })
        
        # Сохраняем данные в FSM
        await state.update_data(
            students_data=students_data,
            works_data=works_data,
            selected_students=[],
            filter_type="all",
            send_to_chat=True,
            send_private=True,
            attached_file=None,
            new_deadline=None,
            throttling_delay=DEFAULT_THROTTLING
        )
        await state.set_state(MassMessagingStates.selecting_students)
        
        await show_student_selection(message, state)


async def show_student_selection(message: Message, state: FSMContext, edit: bool = False):
    """Показать список студентов для связи"""
    data = await state.get_data()
    students_data = data.get('students_data', [])
    
    if not students_data:
        text = "<b>Нет зарегистрированных студентов</b>"
        keyboard = [[InlineKeyboardButton(text="« Назад", callback_data="admin_back")]]
        if edit and message.text:
            await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        else:
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        return
    
    # Формируем сообщение
    text = "<b>Список студентов</b>\n\n"
    text += "Выберите действие рядом с именем студента:\n"
    text += "💬 — начать диалог в боте\n"
    text += "✉️ — открыть в Telegram\n\n"
    
    # Кнопки для каждого студента (две кнопки рядом с именем)
    student_buttons = []
    for student in students_data[:30]:  # Показываем первые 30
        name = student.get('name', 'Без имени')
        telegram_id = student.get('telegram_id', '')
        student_id = student.get('id', '')
        
        # Одна строка с именем и двумя кнопками действий
        # Используем короткие callback_data
        row = [
            InlineKeyboardButton(
                text=f"{name}",
                callback_data=f"student_info:{student_id}"
            ),
            InlineKeyboardButton(
                text="💬",
                callback_data=f"chat_bot:{student_id}"
            ),
        ]
        # Добавляем кнопку открытия в Telegram только если есть telegram_id
        if telegram_id:
            row.append(InlineKeyboardButton(
                text="✉️",
                url=f"tg://user?id={telegram_id}"
            ))
        student_buttons.append(row)
    
    # Кнопка назад
    back_button = [InlineKeyboardButton(text="« Назад в меню", callback_data="admin_back")]
    
    # Собираем клавиатуру
    keyboard = student_buttons + [back_button]
    
    if edit and message.text:
        await message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("filter_type:"))
async def set_filter_type(callback: CallbackQuery, state: FSMContext):
    """Установить фильтр по типу работы"""
    filter_type = callback.data.split(":")[1]
    
    await state.update_data(filter_type=filter_type)
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer(f"Фильтр: {WORK_TYPE_FILTERS.get(filter_type, 'Все')}")


@router.callback_query(F.data == "toggle_send_chat")
async def toggle_send_chat(callback: CallbackQuery, state: FSMContext):
    """Переключить отправку в чат"""
    data = await state.get_data()
    current = data.get('send_to_chat', True)
    await state.update_data(send_to_chat=not current)
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer("☑️ В чат" if not current else "☐ В чат")


@router.callback_query(F.data == "toggle_send_private")
async def toggle_send_private(callback: CallbackQuery, state: FSMContext):
    """Переключить личное сообщение"""
    data = await state.get_data()
    current = data.get('send_private', True)
    await state.update_data(send_private=not current)
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer("☑️ Личное сообщение" if not current else "☐ Личное сообщение")


@router.callback_query(F.data.startswith("toggle_student:"))
async def toggle_student_selection(callback: CallbackQuery, state: FSMContext):
    """Переключить выбор студента"""
    student_id = callback.data.split(":")[1]
    
    data = await state.get_data()
    selected = data.get('selected_students', [])
    
    if student_id in selected:
        selected.remove(student_id)
    else:
        selected.append(student_id)
    
    await state.update_data(selected_students=selected)
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(F.data == "select_all")
async def select_all_students(callback: CallbackQuery, state: FSMContext):
    """Выбрать всех студентов (с учётом фильтра)"""
    data = await state.get_data()
    students_data = data.get('students_data', [])
    works_data = data.get('works_data', {})
    filter_type = data.get('filter_type', 'all')
    
    # Фильтруем студентов
    filtered_students = filter_students_by_work_type(students_data, works_data, filter_type)
    selected = [s['id'] for s in filtered_students]
    
    await state.update_data(selected_students=selected)
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer(f"Выбрано {len(selected)} студентов")


@router.callback_query(F.data == "deselect_all")
async def deselect_all_students(callback: CallbackQuery, state: FSMContext):
    """Снять выбор со всех"""
    await state.update_data(selected_students=[])
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer("Выбор снят")


@router.callback_query(F.data == "go_to_message")
async def go_to_message_composition(callback: CallbackQuery, state: FSMContext):
    """Переход к составлению сообщения"""
    data = await state.get_data()
    selected = data.get('selected_students', [])
    send_to_chat = data.get('send_to_chat', True)
    send_private = data.get('send_private', True)
    
    if not selected:
        await callback.answer("❌ Выберите хотя бы одного студента!", show_alert=True)
        return
    
    if not send_to_chat and not send_private:
        await callback.answer("❌ Выберите хотя бы один способ отправки!", show_alert=True)
        return
    
    await state.set_state(MassMessagingStates.composing_message)
    
    text = f"✉️ <b>Сообщение для {len(selected)} студентов</b>\n\n"
    text += "<b>Настройки:</b>\n"
    text += "☑️ Именное обращение (Привет, {имя}!)\n\n"
    text += "📎 Прикрепить файл: [опционально]\n"
    text += "📅 Новый дедлайн: [опционально]\n"
    text += f"⏱️ Задержка между сообщениями: {DEFAULT_THROTTLING} сек\n\n"
    text += "<b>Введите текст сообщения:</b>\n"
    text += "<i>Используйте {имя} для подстановки имени студента</i>\n\n"
    text += "<b>Например:</b>\n"
    text += '"Привет, {имя}! Напоминаю о дедлайне..."'
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Прикрепить файл", callback_data="attach_file")],
        [InlineKeyboardButton(text="📅 Указать дедлайн", callback_data="set_deadline")],
        [InlineKeyboardButton(text="⚙️ Изменить задержку", callback_data="set_throttling")],
        [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "attach_file")
async def request_file(callback: CallbackQuery, state: FSMContext):
    """Запросить файл для прикрепления"""
    await state.set_state(MassMessagingStates.waiting_for_file)
    
    await callback.message.edit_text(
        "📎 <b>Прикрепление файла</b>\n\n"
        "Отправьте файл (документ, фото, видео).\n"
        "Один файл будет отправлен всем выбранным студентам.\n\n"
        "Или нажмите «Пропустить»",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_file")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_message")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(MassMessagingStates.waiting_for_file)
async def process_attached_file(message: Message, state: FSMContext):
    """Обработка прикреплённого файла"""
    file_info = None
    
    if message.document:
        file_info = {
            'file_id': message.document.file_id,
            'file_name': message.document.file_name,
            'file_type': 'document'
        }
    elif message.photo:
        file_info = {
            'file_id': message.photo[-1].file_id,
            'file_name': 'photo.jpg',
            'file_type': 'photo'
        }
    elif message.video:
        file_info = {
            'file_id': message.video.file_id,
            'file_name': message.video.file_name or 'video.mp4',
            'file_type': 'video'
        }
    
    if file_info:
        await state.update_data(attached_file=file_info)
        await message.answer(
            f"✅ Файл «{file_info['file_name']}» прикреплён!\n\n"
            "Теперь введите текст сообщения:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_message")]
            ])
        )
        await state.set_state(MassMessagingStates.composing_message)
    else:
        await message.answer(
            "❌ Пожалуйста, отправьте файл (документ, фото или видео)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_file")]
            ])
        )


@router.callback_query(F.data == "skip_file")
async def skip_file(callback: CallbackQuery, state: FSMContext):
    """Пропустить прикрепление файла"""
    await state.update_data(attached_file=None)
    await state.set_state(MassMessagingStates.composing_message)
    
    await callback.message.edit_text(
        "✉️ <b>Введите текст сообщения:</b>\n\n"
        "<i>Используйте {имя} для подстановки имени студента</i>\n\n"
        "<b>Например:</b>\n"
        '"Привет, {имя}! Напоминаю о дедлайне..."',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_filters")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_deadline")
async def request_deadline(callback: CallbackQuery, state: FSMContext):
    """Запросить новый дедлайн"""
    await state.set_state(MassMessagingStates.setting_deadline)
    
    await callback.message.edit_text(
        "📅 <b>Установка нового дедлайна</b>\n\n"
        "Введите дату в формате <b>ДД.ММ.ГГГГ</b>\n"
        "Например: 25.04.2026\n\n"
        "Дедлайн будет обновлён у всех выбранных студентов.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_deadline")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_message")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(MassMessagingStates.setting_deadline)
async def process_deadline(message: Message, state: FSMContext):
    """Обработка введённого дедлайна"""
    deadline_text = message.text.strip()
    
    try:
        # Парсим дату
        deadline = datetime.strptime(deadline_text, "%d.%m.%Y")
        deadline = deadline.replace(hour=23, minute=59)
        
        await state.update_data(new_deadline=deadline)
        await state.set_state(MassMessagingStates.composing_message)
        
        await message.answer(
            f"✅ Дедлайн установлен: <b>{deadline_text}</b>\n\n"
            "Теперь введите текст сообщения:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_message")]
            ]),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ\n"
            "Например: 25.04.2026",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_deadline")]
            ])
        )


@router.callback_query(F.data == "skip_deadline")
async def skip_deadline(callback: CallbackQuery, state: FSMContext):
    """Пропустить установку дедлайна"""
    await state.update_data(new_deadline=None)
    await state.set_state(MassMessagingStates.composing_message)
    
    await callback.message.edit_text(
        "✉️ <b>Введите текст сообщения:</b>\n\n"
        "<i>Используйте {имя} для подстановки имени студента</i>\n\n"
        "<b>Например:</b>\n"
        '"Привет, {имя}! Напоминаю о дедлайне..."',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_filters")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_throttling")
async def request_throttling(callback: CallbackQuery, state: FSMContext):
    """Запросить задержку между сообщениями"""
    await state.set_state(MassMessagingStates.setting_throttling)
    
    await callback.message.edit_text(
        f"⚙️ <b>Настройка задержки между сообщениями</b>\n\n"
        f"Текущее значение: <b>{DEFAULT_THROTTLING}</b> сек\n\n"
        "Введите новое значение (в секундах):\n"
        "Рекомендуется: 10-30 сек (чтобы избежать блокировки)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_message")]
        ]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(MassMessagingStates.setting_throttling)
async def process_throttling(message: Message, state: FSMContext):
    """Обработка задержки"""
    try:
        delay = int(message.text.strip())
        if delay < 1 or delay > 300:
            raise ValueError("Delay out of range")
        
        await state.update_data(throttling_delay=delay)
        await state.set_state(MassMessagingStates.composing_message)
        
        await message.answer(
            f"✅ Задержка установлена: <b>{delay}</b> сек\n\n"
            "Теперь введите текст сообщения:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_message")]
            ]),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Введите число от 1 до 300 (секунд)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_message")]
            ])
        )


@router.callback_query(F.data == "back_to_filters")
async def back_to_filters(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору студентов"""
    await state.set_state(MassMessagingStates.selecting_students)
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(F.data == "back_to_message")
async def back_to_message(callback: CallbackQuery, state: FSMContext):
    """Вернуться к вводу сообщения"""
    await state.set_state(MassMessagingStates.composing_message)
    
    data = await state.get_data()
    attached_file = data.get('attached_file')
    new_deadline = data.get('new_deadline')
    throttling_delay = data.get('throttling_delay', DEFAULT_THROTTLING)
    
    text = "✉️ <b>Составление сообщения</b>\n\n"
    
    if attached_file:
        text += f"📎 Файл: <b>{attached_file['file_name']}</b>\n"
    else:
        text += "📎 Файл: <i>не прикреплён</i>\n"
    
    if new_deadline:
        text += f"📅 Дедлайн: <b>{new_deadline.strftime('%d.%m.%Y')}</b>\n"
    else:
        text += "📅 Дедлайн: <i>не указан</i>\n"
    
    text += f"⏱️ Задержка: <b>{throttling_delay}</b> сек\n\n"
    text += "<b>Введите текст сообщения:</b>\n"
    text += "<i>Используйте {имя} для подстановки имени студента</i>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Прикрепить файл", callback_data="attach_file")],
        [InlineKeyboardButton(text="📅 Указать дедлайн", callback_data="set_deadline")],
        [InlineKeyboardButton(text="⚙️ Изменить задержку", callback_data="set_throttling")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_filters")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(MassMessagingStates.composing_message)
async def process_message_text(message: Message, state: FSMContext):
    """Обработка текста сообщения"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Рассылка отменена.", reply_markup=get_admin_menu())
        return
    
    message_text = message.text
    
    await state.update_data(message_text=message_text)
    
    # Переходим к подтверждению
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Показать подтверждение перед отправкой"""
    data = await state.get_data()
    selected_count = len(data.get('selected_students', []))
    message_text = data.get('message_text', '')
    attached_file = data.get('attached_file')
    new_deadline = data.get('new_deadline')
    throttling_delay = data.get('throttling_delay', DEFAULT_THROTTLING)
    send_to_chat = data.get('send_to_chat', True)
    send_private = data.get('send_private', True)
    
    # Показываем предпросмотр
    preview_text = "👁️ <b>Предпросмотр рассылки</b>\n\n"
    
    # Пример для студента
    preview_text += "<i>Пример для студента Иванов И.И.:</i>\n"
    preview_text += "━" * 20 + "\n"
    
    # Добавляем приветствие
    greeting = "Привет, Иванов И.И.! 👋\n\n" if "{имя}" in message_text else ""
    preview_text += greeting + message_text.replace("{имя}", "Иванов И.И.") + "\n"
    preview_text += "━" * 20 + "\n\n"
    
    # Информация о рассылке
    preview_text += f"📊 <b>Параметры рассылки:</b>\n"
    preview_text += f"• Получателей: <b>{selected_count}</b>\n"
    preview_text += f"• Задержка: <b>{throttling_delay}</b> сек\n"
    preview_text += f"• Примерное время: <b>{selected_count * throttling_delay // 60}</b> мин\n"
    
    if attached_file:
        preview_text += f"• Файл: <b>{attached_file['file_name']}</b>\n"
    
    if new_deadline:
        preview_text += f"• Новый дедлайн: <b>{new_deadline.strftime('%d.%m.%Y')}</b>\n"
    
    preview_text += f"• Отправка: {'в чат' if send_to_chat else ''} {'+ лично' if send_private else ''}\n\n"
    preview_text += "<b>Отправить сообщения?</b>"
    
    await message.answer(
        preview_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👁️ Предпросмотр", callback_data="preview_message"),
            ],
            [
                InlineKeyboardButton(text="📤 Отправить", callback_data="confirm_send"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_message")
            ],
            [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(MassMessagingStates.confirming_send)


@router.callback_query(F.data == "preview_message")
async def preview_message(callback: CallbackQuery, state: FSMContext):
    """Показать полный предпросмотр"""
    data = await state.get_data()
    message_text = data.get('message_text', '')
    attached_file = data.get('attached_file')
    
    await callback.answer("Отправляю пример...")
    
    # Отправляем пример админу
    example_text = message_text.replace("{имя}", callback.from_user.full_name or "Администратор")
    
    await callback.message.answer("👁️ <b>Пример сообщения:</b>\n\n" + example_text, parse_mode="HTML")
    
    if attached_file:
        await callback.message.answer(f"📎 <b>Прикреплённый файл:</b> {attached_file['file_name']}")


@router.callback_query(F.data == "confirm_send")
async def confirm_and_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и отправка сообщений с throttling"""
    data = await state.get_data()
    selected_ids = data.get('selected_students', [])
    message_text = data.get('message_text', '')
    attached_file = data.get('attached_file')
    new_deadline = data.get('new_deadline')
    throttling_delay = data.get('throttling_delay', DEFAULT_THROTTLING)
    send_to_chat = data.get('send_to_chat', True)
    send_private = data.get('send_private', True)
    
    if not selected_ids or not message_text:
        await callback.answer("❌ Ошибка данных!", show_alert=True)
        return
    
    # Отправляем начальное сообщение о прогрессе
    progress_msg = await callback.message.edit_text(
        f"📤 <b>Начинаю рассылку...</b>\n"
        f"Всего: {len(selected_ids)} студентов\n"
        f"Отправлено: 0/{len(selected_ids)}\n"
        f"⏱️ Задержка: {throttling_delay} сек",
        parse_mode="HTML"
    )
    
    # Получаем данные студентов из БД
    sent_count = 0
    failed_count = 0
    updated_deadlines = 0
    
    async with AsyncSessionContext() as session:
        from bot.models import Communication
        from uuid import uuid4
        
        for i, student_id in enumerate(selected_ids):
            result = await session.execute(
                select(User).where(User.id == student_id)
            )
            student = result.scalar_one_or_none()
            
            if not student:
                failed_count += 1
                continue
            
            # Формируем персонализированное сообщение
            first_name = student.full_name.split()[0] if student.full_name else "Студент"
            personalized_text = message_text.replace("{имя}", student.full_name or "Студент")
            
            # Добавляем приветствие если есть {имя}
            if "{имя}" in message_text:
                personalized_text = f"Привет, {first_name}! 👋\n\n" + personalized_text
            
            try:
                # Отправляем через бота (если включена отправка в чат)
                if send_to_chat:
                    # Отправляем текст
                    await bot.send_message(
                        chat_id=student.telegram_id,
                        text=personalized_text,
                        parse_mode="HTML"
                    )
                    
                    # Отправляем файл если есть
                    if attached_file:
                        if attached_file['file_type'] == 'document':
                            await bot.send_document(
                                chat_id=student.telegram_id,
                                document=attached_file['file_id'],
                                caption=f"📎 Файл от преподавателя"
                            )
                        elif attached_file['file_type'] == 'photo':
                            await bot.send_photo(
                                chat_id=student.telegram_id,
                                photo=attached_file['file_id'],
                                caption=f"📎 Фото от преподавателя"
                            )
                        elif attached_file['file_type'] == 'video':
                            await bot.send_video(
                                chat_id=student.telegram_id,
                                video=attached_file['file_id'],
                                caption=f"📎 Видео от преподавателя"
                            )
                
                # Личное сообщение (если включено и отличается от чата)
                if send_private and send_to_chat:
                    # В aiogram нет прямого способа отправить "личное сообщение" отдельно от бота
                    # Это просто дубликат для ясности
                    pass
                
                # Сохраняем в communications (для истории)
                if send_to_chat:
                    comm = Communication(
                        id=uuid4(),
                        from_user_id=None,
                        to_user_id=student_id,
                        channel="telegram",
                        message_type="text",
                        message=personalized_text,
                        content=personalized_text,
                        from_student=False,
                        from_teacher=True,
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    session.add(comm)
                
                sent_count += 1
                
                # Обновляем дедлайн если указан
                if new_deadline:
                    # Находим активную работу студента
                    result = await session.execute(
                        select(StudentWork).where(
                            and_(
                                StudentWork.student_id == student_id,
                                StudentWork.status.notin_(['accepted', 'rejected'])
                            )
                        ).order_by(StudentWork.created_at.desc())
                    )
                    active_work = result.scalar_one_or_none()
                    
                    if active_work:
                        active_work.deadline = new_deadline
                        updated_deadlines += 1
                
                # Обновляем прогресс каждые 5 сообщений
                if (i + 1) % 5 == 0 or (i + 1) == len(selected_ids):
                    await progress_msg.edit_text(
                        f"📤 <b>Рассылка в процессе...</b>\n"
                        f"Всего: {len(selected_ids)} студентов\n"
                        f"Отправлено: {sent_count}/{len(selected_ids)}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"📅 Обновлено дедлайнов: {updated_deadlines}\n"
                        f"⏱️ Задержка: {throttling_delay} сек",
                        parse_mode="HTML"
                    )
                
                # Throttling - КРИТИЧЕСКИ ВАЖНО!
                await asyncio.sleep(throttling_delay)
                
            except Exception as e:
                logger.error(f"Failed to send message to {student_id}: {e}")
                failed_count += 1
        
        # Сохраняем все communications и обновления дедлайнов
        await session.commit()
    
    # Финальное сообщение
    final_text = (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Отправлено: <b>{sent_count}</b>\n"
        f"❌ Ошибок: <b>{failed_count}</b>\n"
    )
    
    if new_deadline:
        final_text += f"📅 Обновлено дедлайнов: <b>{updated_deadlines}</b>\n"
    
    final_text += "📁 Сохранено в истории переписки"
    
    await progress_msg.edit_text(final_text, parse_mode="HTML")
    
    await state.clear()
    await callback.message.answer(
        "Вернуться в меню администратора:",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "edit_message")
async def edit_message(callback: CallbackQuery, state: FSMContext):
    """Вернуться к редактированию сообщения"""
    await state.set_state(MassMessagingStates.composing_message)
    
    data = await state.get_data()
    attached_file = data.get('attached_file')
    new_deadline = data.get('new_deadline')
    throttling_delay = data.get('throttling_delay', DEFAULT_THROTTLING)
    
    text = "✏️ <b>Редактирование сообщения</b>\n\n"
    
    if attached_file:
        text += f"📎 Файл: <b>{attached_file['file_name']}</b>\n"
    
    if new_deadline:
        text += f"📅 Дедлайн: <b>{new_deadline.strftime('%d.%m.%Y')}</b>\n"
    
    text += f"⏱️ Задержка: <b>{throttling_delay}</b> сек\n\n"
    text += "<b>Введите новый текст сообщения:</b>\n"
    text += "<i>Используйте {имя} для подстановки имени студента</i>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Прикрепить файл", callback_data="attach_file")],
        [InlineKeyboardButton(text="📅 Указать дедлайн", callback_data="set_deadline")],
        [InlineKeyboardButton(text="⚙️ Изменить задержку", callback_data="set_throttling")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_filters")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await callback.message.edit_text("🚫 Рассылка отменена.")
    await callback.message.answer(
        "Главное меню администратора:",
        reply_markup=get_admin_menu()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("chat_bot:"))
async def start_chat_with_student(callback: CallbackQuery, state: FSMContext):
    """Начать диалог со студентом в боте"""
    student_id = callback.data.split(":")[1]
    
    # Get student data from state
    data = await state.get_data()
    students_data = data.get('students_data', [])
    
    # Find student by ID
    student = None
    for s in students_data:
        if str(s.get('id')) == student_id:
            student = s
            break
    
    if not student:
        await callback.answer("Студент не найден", show_alert=True)
        return
    
    student_name = student.get('name', 'Студент')
    student_tg_id = student.get('telegram_id', '')
    
    # Store current student for communication
    await state.update_data(
        communication_student_id=student_id,
        communication_student_name=student_name,
        communication_student_tg_id=student_tg_id
    )
    
    # Start communication state
    from bot.handlers.communication import CommunicationStates
    await state.set_state(CommunicationStates.waiting_message)
    await state.update_data(
        recipient_id=student_tg_id,
        recipient_name=student_name,
        recipient_role="student"
    )
    
    text = f"""<b>Диалог с {student_name}</b>

Введите ваше сообщение:
<i>Оно будет отправлено студенту в этом боте.</i>

Для отмены нажмите «Назад»"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Назад к списку", callback_data="back_to_students")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer(f"Начат диалог с {student_name}")


@router.callback_query(F.data == "back_to_students")
async def back_to_students(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку студентов"""
    await state.set_state(MassMessagingStates.selecting_students)
    await show_student_selection(callback.message, state, edit=True)
    await callback.answer()


# ========== WEB AUTH KEY GENERATION ==========

@router.message(F.text == "🔑 Ключи веб-доступа")
async def start_web_auth_key_generation(message: Message, state: FSMContext):
    """Начать генерацию ключа веб-доступа для студента"""
    telegram_id = message.from_user.id
    
    if telegram_id not in config.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой функции.")
        return
    
    async with AsyncSessionContext() as session:
        # Получаем всех студентов
        result = await session.execute(
            select(User).where(
                User.role.in_(['student', 'aspirant'])
            ).order_by(User.full_name)
        )
        students = result.scalars().all()
        
        if not students:
            await message.answer("❌ Нет зарегистрированных студентов.")
            return
        
        # Формируем список студентов
        text = "<b>🔑 Генерация ключа веб-доступа</b>\n\n"
        text += "Выберите студента для генерации ключа:\n\n"
        
        keyboard = []
        for student in students[:20]:  # Показываем первые 20
            name = student.full_name or f"User_{student.telegram_id}"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{name}",
                    callback_data=f"generate_key:{student.id}:{student.telegram_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="« Назад", callback_data="admin_back")])
        
        await state.set_state(WebAuthStates.selecting_student_for_auth)
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("generate_key:"))
async def generate_web_auth_key(callback: CallbackQuery, state: FSMContext):
    """Сгенерировать ключ веб-доступа для студента"""
    parts = callback.data.split(":")
    student_id = parts[1]
    student_tg_id = parts[2] if len(parts) > 2 else None
    
    from datetime import timedelta
    import secrets
    
    async with AsyncSessionContext() as session:
        # Получаем данные студента
        result = await session.execute(
            select(User).where(User.id == student_id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            await callback.answer("Студент не найден", show_alert=True)
            return
        
        # Генерируем ключ
        auth_code = secrets.token_urlsafe(8)[:12].upper()
        
        # Устанавливаем срок действия (7 дней)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        # Создаем запись в БД
        from uuid import uuid4
        web_auth = WebAuthCode(
            id=uuid4(),
            user_id=student_id,
            code=auth_code,
            generated_by='admin',
            expires_at=expires_at,
            is_used=False
        )
        session.add(web_auth)
        await session.commit()
        
        # Формируем ссылки
        web_url = "https://familypaper.online"  # Или из конфига
        auth_url = f"{web_url}/auth?code={auth_code}"
        
        # Отправляем админу
        text = f"""<b>✅ Ключ веб-доступа сгенерирован!</b>

👤 Студент: <b>{student.full_name}</b>
📧 Email: {student.email or 'не указан'}

🔑 <b>Код доступа:</b> <code>{auth_code}</code>
⏰ Срок действия: до {expires_at.strftime('%d.%m.%Y %H:%M')}

🔗 <b>Прямая ссылка:</b>
<code>{auth_url}</code>

<b>Как использовать:</b>
1. Отправьте код студенту
2. Студент переходит по ссылке или вводит код на сайте
3. Код действует 7 дней
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Отправить студенту", callback_data=f"send_key:{student.telegram_id}:{auth_code}")],
            [InlineKeyboardButton(text="🔄 Сгенерировать новый", callback_data=f"generate_key:{student_id}:{student_tg_id}")],
            [InlineKeyboardButton(text="« К списку студентов", callback_data="back_to_web_auth")],
            [InlineKeyboardButton(text="« В админ-меню", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer("Ключ сгенерирован!")


@router.callback_query(F.data.startswith("send_key:"))
async def send_key_to_student(callback: CallbackQuery, state: FSMContext):
    """Отправить ключ студенту в Telegram"""
    parts = callback.data.split(":")
    student_tg_id = int(parts[1])
    auth_code = parts[2]
    
    web_url = "https://familypaper.online"
    auth_url = f"{web_url}/auth?code={auth_code}"
    
    try:
        # Отправляем студенту
        await callback.bot.send_message(
            chat_id=student_tg_id,
            text=f"""<b>🔑 Вам предоставлен доступ к веб-порталу!</b>

🔑 <b>Ваш код доступа:</b> <code>{auth_code}</code>

🔗 <b>Перейдите по ссылке:</b>
{auth_url}

⏰ Код действует 7 дней.

После входа вы сможете:
• Просматривать свои работы
• Сдавать новые работы
• Общаться с руководителем
• Отслеживать дедлайны
""",
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Ключ отправлен студенту!")
        await callback.message.answer("✅ Ключ успешно отправлен студенту в личные сообщения!")
        
    except Exception as e:
        logger.error(f"Failed to send key to student: {e}")
        await callback.answer("❌ Не удалось отправить ключ", show_alert=True)
        await callback.message.answer(
            f"❌ Не удалось отправить ключ студенту.\n"
            f"Возможно, студент заблокировал бота или не начал диалог.\n\n"
            f"Отправьте код вручную: <code>{auth_code}</code>",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back_to_web_auth")
async def back_to_web_auth(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку студентов для генерации ключей"""
    await start_web_auth_key_generation(callback.message, state)
    await callback.answer()
