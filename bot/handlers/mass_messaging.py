"""
DigitalTutor Bot - Mass Messaging Handler
Массовые рассылки для администратора
"""
import logging
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from datetime import datetime

from bot.keyboards import get_admin_menu, get_cancel_menu
from bot.models import AsyncSessionContext, User, StudentWork

logger = logging.getLogger(__name__)
router = Router()

# FSM States для массовой рассылки
class MassMessagingStates(StatesGroup):
    selecting_students = State()
    composing_message = State()
    confirming_send = State()

# Хранение данных рассылки (временно, для FSM)
# В продакшене лучше использовать Redis или базу данных

ADMIN_IDS = [502621151]

# Настройка throttling (в секундах)
DEFAULT_THROTTLING = 15


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


def get_student_status_color(student_id, works) -> str:
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


def get_student_work_status(student_id, works) -> str:
    """Получить статус последней работы студента"""
    if not works:
        return "нет работ"
    
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
    
    status_text = STATUS_MAP.get(latest_work.status, latest_work.status)
    work_type = latest_work.work_type or "работа"
    
    return f"{work_type} ({status_text})"


@router.message(F.text == "📤 Массовая рассылка")
async def start_mass_messaging(message: Message, state: FSMContext):
    """Начать массовую рассылку - шаг 1: выбор студентов"""
    telegram_id = message.from_user.id
    
    if telegram_id not in ADMIN_IDS:
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
        
        # Получаем работы для определения статуса
        students_data = []
        for student in students:
            result = await session.execute(
                select(StudentWork).where(StudentWork.student_id == student.id)
            )
            works = result.scalars().all()
            
            color = get_student_status_color(student.id, works)
            work_status = get_student_work_status(student.id, works)
            
            students_data.append({
                'id': str(student.id),
                'name': student.full_name or f"User_{student.telegram_id}",
                'color': color,
                'work_status': work_status,
                'group': student.group_name or "—"
            })
        
        # Сохраняем данные в FSM
        await state.update_data(students_data=students_data, selected_students=[])
        await state.set_state(MassMessagingStates.selecting_students)
        
        # Формируем сообщение
        text = "📤 <b>Массовая рассылка</b>\n\n"
        text += "<b>Шаг 1:</b> Выберите студентов\n\n"
        text += "Фильтры: [Все] [🔴] [🟡] [🟢]\n\n"
        
        # Кнопки для выбора студентов (по 1 в строке для удобства)
        keyboard = []
        for student in students_data[:20]:  # Показываем первые 20
            emoji = "☑️" if student['id'] in [] else "☐"
            keyboard.append([InlineKeyboardButton(
                text=f"{student['color']} {emoji} {student['name']} — {student['work_status']}",
                callback_data=f"toggle_student:{student['id']}"
            )])
        
        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton(text="✅ Выбрать все", callback_data="select_all"),
            InlineKeyboardButton(text="❌ Снять все", callback_data="deselect_all")
        ])
        keyboard.append([
            InlineKeyboardButton(text="➡️ Далее", callback_data="go_to_message")
        ])
        keyboard.append([
            InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")
        ])
        
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("toggle_student:"))
async def toggle_student_selection(callback: CallbackQuery, state: FSMContext):
    """Переключить выбор студента"""
    student_id = callback.data.split(":")[1]
    
    data = await state.get_data()
    selected = data.get('selected_students', [])
    students_data = data.get('students_data', [])
    
    if student_id in selected:
        selected.remove(student_id)
    else:
        selected.append(student_id)
    
    await state.update_data(selected_students=selected)
    
    # Обновляем клавиатуру
    keyboard = []
    for student in students_data[:20]:
        emoji = "☑️" if student['id'] in selected else "☐"
        keyboard.append([InlineKeyboardButton(
            text=f"{student['color']} {emoji} {student['name']} — {student['work_status']}",
            callback_data=f"toggle_student:{student['id']}"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="✅ Выбрать все", callback_data="select_all"),
        InlineKeyboardButton(text="❌ Снять все", callback_data="deselect_all")
    ])
    keyboard.append([
        InlineKeyboardButton(text=f"➡️ Далее ({len(selected)} выбрано)", callback_data="go_to_message")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")
    ])
    
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data == "select_all")
async def select_all_students(callback: CallbackQuery, state: FSMContext):
    """Выбрать всех студентов"""
    data = await state.get_data()
    students_data = data.get('students_data', [])
    selected = [s['id'] for s in students_data]
    
    await state.update_data(selected_students=selected)
    
    # Обновляем клавиатуру
    keyboard = []
    for student in students_data[:20]:
        keyboard.append([InlineKeyboardButton(
            text=f"{student['color']} ☑️ {student['name']} — {student['work_status']}",
            callback_data=f"toggle_student:{student['id']}"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="✅ Выбрать все", callback_data="select_all"),
        InlineKeyboardButton(text="❌ Снять все", callback_data="deselect_all")
    ])
    keyboard.append([
        InlineKeyboardButton(text=f"➡️ Далее ({len(selected)} выбрано)", callback_data="go_to_message")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")
    ])
    
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer(f"Выбрано {len(selected)} студентов")


@router.callback_query(F.data == "deselect_all")
async def deselect_all_students(callback: CallbackQuery, state: FSMContext):
    """Снять выбор со всех"""
    data = await state.get_data()
    students_data = data.get('students_data', [])
    
    await state.update_data(selected_students=[])
    
    # Обновляем клавиатуру
    keyboard = []
    for student in students_data[:20]:
        keyboard.append([InlineKeyboardButton(
            text=f"{student['color']} ☐ {student['name']} — {student['work_status']}",
            callback_data=f"toggle_student:{student['id']}"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="✅ Выбрать все", callback_data="select_all"),
        InlineKeyboardButton(text="❌ Снять все", callback_data="deselect_all")
    ])
    keyboard.append([
        InlineKeyboardButton(text="➡️ Далее (0 выбрано)", callback_data="go_to_message")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")
    ])
    
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer("Выбор снят")


@router.callback_query(F.data == "go_to_message")
async def go_to_message_composition(callback: CallbackQuery, state: FSMContext):
    """Переход к составлению сообщения"""
    data = await state.get_data()
    selected = data.get('selected_students', [])
    
    if not selected:
        await callback.answer("❌ Выберите хотя бы одного студента!", show_alert=True)
        return
    
    await state.set_state(MassMessagingStates.composing_message)
    
    text = f"✉️ <b>Сообщение для {len(selected)} студентов</b>\n\n"
    text += "Настройки:\n"
    text += "☑️ Именное обращение включено (автоматически)\n\n"
    text += "Введите текст сообщения:\n"
    text += "<i>Используйте {'{имя}'} для подстановки имени студента</i>\n\n"
    text += "Например:\n"
    text += '"Привет, {имя}! Напоминаю о дедлайне..."'
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")]
        ]),
        parse_mode="HTML"
    )
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
    await state.set_state(MassMessagingStates.confirming_send)
    
    data = await state.get_data()
    selected_count = len(data.get('selected_students', []))
    
    # Показываем предпросмотр
    preview_text = f"👁️ <b>Предпросмотр сообщения:</b>\n\n"
    preview_text += f"<i>Пример для студента Иванов И.И.:</i>\n"
    preview_text += "━" * 20 + "\n"
    preview_text += message_text.replace("{имя}", "Иванов И.И.") + "\n"
    preview_text += "━" * 20 + "\n\n"
    preview_text += f"📊 Будет отправлено: <b>{selected_count}</b> студентам\n"
    preview_text += f"⏱️ Задержка между сообщениями: <b>{DEFAULT_THROTTLING}</b> сек\n"
    preview_text += f"⏱️ Примерное время: <b>{selected_count * DEFAULT_THROTTLING // 60}</b> мин\n\n"
    preview_text += "Отправить?"
    
    await message.answer(
        preview_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Отправить", callback_data="confirm_send"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="edit_message")
            ],
            [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")]
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "confirm_send")
async def confirm_and_send(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и отправка сообщений"""
    data = await state.get_data()
    selected_ids = data.get('selected_students', [])
    message_text = data.get('message_text', '')
    
    if not selected_ids or not message_text:
        await callback.answer("❌ Ошибка данных!", show_alert=True)
        return
    
    # Отправляем начальное сообщение о прогрессе
    progress_msg = await callback.message.edit_text(
        f"📤 <b>Начинаю рассылку...</b>\n"
        f"Всего: {len(selected_ids)} студентов\n"
        f"Отправлено: 0/{len(selected_ids)}\n"
        f"⏱️ Задержка: {DEFAULT_THROTTLING} сек",
        parse_mode="HTML"
    )
    
    # Получаем данные студентов из БД
    sent_count = 0
    failed_count = 0
    
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
            personalized_text = message_text.replace("{имя}", student.full_name or "Студент")
            
            try:
                # Отправляем через бота (канал 1: в чат + сохранение в БД)
                await callback.bot.send_message(
                    chat_id=student.telegram_id,
                    text=personalized_text,
                    parse_mode="HTML"
                )
                
                # Сохраняем в communications (для истории)
                comm = Communication(
                    id=uuid4(),
                    from_user_id=None,  # Системное сообщение
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
                
                # Обновляем прогресс каждые 5 сообщений
                if (i + 1) % 5 == 0:
                    await progress_msg.edit_text(
                        f"📤 <b>Рассылка в процессе...</b>\n"
                        f"Всего: {len(selected_ids)} студентов\n"
                        f"Отправлено: {sent_count}/{len(selected_ids)}\n"
                        f"❌ Ошибок: {failed_count}\n"
                        f"⏱️ Задержка: {DEFAULT_THROTTLING} сек",
                        parse_mode="HTML"
                    )
                
                # Throttling
                await asyncio.sleep(DEFAULT_THROTTLING)
                
            except Exception as e:
                logger.error(f"Failed to send message to {student_id}: {e}")
                failed_count += 1
        
        # Сохраняем все communications
        await session.commit()
    
    # Финальное сообщение
    await progress_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📊 Отправлено: <b>{sent_count}</b>\n"
        f"❌ Ошибок: <b>{failed_count}</b>\n"
        f"📁 Сохранено в истории переписки",
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.message.answer(
        "Вернуться в меню администратора:",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "edit_message")
async def edit_message(callback: CallbackQuery, state: FSMContext):
    """Вернуться к редактированию сообщения"""
    await state.set_state(MassMessagingStates.composing_message)
    
    text = "✏️ <b>Введите новый текст сообщения:</b>\n\n"
    text += "<i>Используйте {'{имя}'} для подстановки имени студента</i>"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_broadcast")]
        ]),
        parse_mode="HTML"
    )
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
