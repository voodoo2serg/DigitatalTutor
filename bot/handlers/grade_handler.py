"""
DigitalTutor Bot - Grade Handler
Трёхкомпонентная оценка работ с кнопками финального статуса
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from datetime import datetime
from uuid import uuid4

from bot.models import AsyncSessionContext, StudentWork, User, Communication

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = [502621151]


class GradeStates(StatesGroup):
    waiting_classic = State()
    waiting_100 = State()
    waiting_letter = State()
    waiting_comment = State()


# Маппинг 100-балльной в классическую
GRADE_100_TO_CLASSIC = {
    (90, 100): 5,
    (75, 89): 4,
    (60, 74): 3,
    (0, 59): 2,
}

# Маппинг 100-балльной в буквенную
GRADE_100_TO_LETTER = {
    (90, 100): "A",
    (80, 89): "B",
    (70, 79): "C",
    (60, 69): "D",
    (0, 59): "E",
}


def convert_100_to_classic(grade_100):
    """Конвертировать 100-балльную в классическую"""
    for (min_val, max_val), classic in GRADE_100_TO_CLASSIC.items():
        if min_val <= grade_100 <= max_val:
            return classic
    return None


def convert_100_to_letter(grade_100):
    """Конвертировать 100-балльную в буквенную"""
    for (min_val, max_val), letter in GRADE_100_TO_LETTER.items():
        if min_val <= grade_100 <= max_val:
            return letter
    return None


@router.callback_query(F.data.startswith("grade_work:"))
async def start_grading(callback: CallbackQuery, state: FSMContext):
    """Начало процесса оценки работы"""
    work_id = callback.data.split(":")[1]
    
    await state.update_data(work_id=work_id)
    await state.set_state(GradeStates.waiting_classic)
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await callback.answer("❌ Работа не найдена", show_alert=True)
            return
        
        text = f"⭐ <b>Выставление оценки</b>\n\n"
        text += f"Работа: {work.title}\n"
        text += f"Тип: {work.work_type or '—'}\n\n"
        text += "Заполните поля (минимум одно):\n\n"
        text += "🏫 <b>Классическая оценка (1-5):</b>\n"
        text += "Выберите или введите число:"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="grade_classic:1"),
                InlineKeyboardButton(text="2", callback_data="grade_classic:2"),
                InlineKeyboardButton(text="3", callback_data="grade_classic:3"),
                InlineKeyboardButton(text="4", callback_data="grade_classic:4"),
                InlineKeyboardButton(text="5", callback_data="grade_classic:5"),
            ],
            [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_classic")],
            [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_grade")],
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("grade_classic:"))
async def set_classic_grade(callback: CallbackQuery, state: FSMContext):
    """Установить классическую оценку"""
    grade = int(callback.data.split(":")[1])
    await state.update_data(grade_classic=grade)
    await state.set_state(GradeStates.waiting_100)
    
    text = "⭐ <b>Выставление оценки</b>\n\n"
    text += f"✅ Классическая: <b>{grade}</b>\n\n"
    text += "📊 <b>100-бальная оценка (0-100):</b>\n"
    text += "Введите число или пропустите:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_100")],
        [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_grade")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "skip_classic")
async def skip_classic(callback: CallbackQuery, state: FSMContext):
    """Пропустить классическую оценку"""
    await state.set_state(GradeStates.waiting_100)
    
    text = "⭐ <b>Выставление оценки</b>\n\n"
    text += "⏭️ Классическая: пропущено\n\n"
    text += "📊 <b>100-бальная оценка (0-100):</b>\n"
    text += "Введите число или пропустите:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_100")],
        [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_grade")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "skip_100")
async def skip_100(callback: CallbackQuery, state: FSMContext):
    """Пропустить 100-бальную оценку"""
    await state.set_state(GradeStates.waiting_letter)
    
    text = "⭐ <b>Выставление оценки</b>\n\n"
    text += "⏭️ 100-бальная: пропущено\n\n"
    text += "🅱️ <b>Буквенная оценка:</b>\n"
    text += "Выберите или пропустите:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="A", callback_data="grade_letter:A"),
            InlineKeyboardButton(text="B", callback_data="grade_letter:B"),
            InlineKeyboardButton(text="C", callback_data="grade_letter:C"),
            InlineKeyboardButton(text="D", callback_data="grade_letter:D"),
            InlineKeyboardButton(text="E", callback_data="grade_letter:E"),
        ],
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_letter")],
        [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_grade")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("grade_letter:"))
async def set_letter_grade(callback: CallbackQuery, state: FSMContext):
    """Установить буквенную оценку"""
    letter = callback.data.split(":")[1]
    await state.update_data(grade_letter=letter)
    
    await ask_for_comment(callback, state)


@router.callback_query(F.data == "skip_letter")
async def skip_letter(callback: CallbackQuery, state: FSMContext):
    """Пропустить буквенную оценку"""
    await ask_for_comment(callback, state)


async def ask_for_comment(callback: CallbackQuery, state: FSMContext):
    """Запросить комментарий"""
    await state.set_state(GradeStates.waiting_comment)
    
    data = await state.get_data()
    
    text = "⭐ <b>Выставление оценки</b>\n\n"
    text += "<b>Введённые данные:</b>\n"
    
    if data.get('grade_classic'):
        text += f"🏫 Классическая: {data['grade_classic']}\n"
    
    if data.get('grade_100'):
        text += f"📊 100-бальная: {data['grade_100']}\n"
    
    if data.get('grade_letter'):
        text += f"🅱️ Буквенная: {data['grade_letter']}\n"
    
    text += "\n💬 <b>Комментарий к оценке:</b>\n"
    text += "Введите текст или пропустите:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_comment")],
        [InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_grade")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "skip_comment")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    """Пропустить комментарий и показать финальные кнопки"""
    await show_final_buttons(callback, state)


async def show_final_buttons(callback: CallbackQuery, state: FSMContext):
    """Показать финальные кнопки статуса"""
    data = await state.get_data()
    work_id = data.get('work_id')
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await callback.answer("❌ Работа не найдена", show_alert=True)
            return
        
        text = "⭐ <b>Подтверждение оценки</b>\n\n"
        text += f"Работа: {work.title}\n"
        text += f"Тип: {work.work_type or '—'}\n\n"
        
        if data.get('grade_classic'):
            text += f"🏫 Классическая: {data['grade_classic']}\n"
        
        if data.get('grade_100'):
            text += f"📊 100-бальная: {data['grade_100']}\n"
        
        if data.get('grade_letter'):
            text += f"🅱️ Буквенная: {data['grade_letter']}\n"
        
        text += "\n<b>Выберите финальный статус:</b>\n"
        text += "<i>(оцениваются только курсовые и проекты)\u003c/i>"
        
        # Определяем тип работы для правильной кнопки
        work_type = work.work_type or ""
        is_article = "стать" in work_type.lower()
        is_vkr = "вкр" in work_type.lower() or "бакалавр" in work_type.lower() or "магистр" in work_type.lower()
        is_coursework = "курсов" in work_type.lower()
        
        keyboard_buttons = []
        
        if is_article:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="✅ Согласовано для публикации",
                    callback_data="final_status:approved_for_publication"
                )
            ])
        elif is_vkr:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="✅ Допущено к защите",
                    callback_data="final_status:admitted_to_defense"
                )
            ])
        elif is_coursework:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text="✅ Оценено",
                    callback_data="final_status:graded"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="💾 Сохранить без статуса", callback_data="final_status:save_only"),
        ])
        keyboard_buttons.append([
            InlineKeyboardButton(text="🚫 Отмена", callback_data="cancel_grade"),
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("final_status:"))
async def save_grade_and_status(callback: CallbackQuery, state: FSMContext):
    """Сохранить оценку и статус"""
    final_status = callback.data.split(":")[1]
    data = await state.get_data()
    work_id = data.get('work_id')
    
    if not work_id:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await callback.answer("❌ Работа не найдена", show_alert=True)
            return
        
        # Собираем данные оценки
        grade_classic = data.get('grade_classic')
        grade_100 = data.get('grade_100')
        grade_letter = data.get('grade_letter')
        
        # Автоконвертация если только одна оценка
        if grade_100 and not grade_classic:
            grade_classic = convert_100_to_classic(grade_100)
        
        if grade_100 and not grade_letter:
            grade_letter = convert_100_to_letter(grade_100)
        
        # Определяем статус работы
        new_status = work.status
        is_archived = False
        
        if final_status == "approved_for_publication":
            new_status = "approved_for_publication"
            is_archived = True
        elif final_status == "admitted_to_defense":
            new_status = "admitted_to_defense"
            is_archived = True
        elif final_status == "graded":
            new_status = "graded"
            is_archived = True
        
        # Обновляем работу
        from sqlalchemy import update
        await session.execute(
            update(StudentWork)
            .where(StudentWork.id == work_id)
            .values(
                grade_classic=grade_classic,
                grade_100=grade_100,
                grade_letter=grade_letter,
                status=new_status,
                is_archived=is_archived,
                graded_at=datetime.utcnow()
            )
        )
        await session.commit()
        
        # Отправляем уведомление студенту
        try:
            student_result = await session.execute(
                select(User).where(User.id == work.student_id)
            )
            student = student_result.scalar_one_or_none()
            
            if student:
                status_text = {
                    "approved_for_publication": "✅ Согласовано для публикации",
                    "admitted_to_defense": "✅ Допущено к защите",
                    "graded": "✅ Оценено",
                }.get(final_status, "Сохранено")
                
                grade_text = "📊 Ваша работа оценена!\n\n"
                grade_text += f"Работа: {work.title}\n\n"
                
                if grade_classic:
                    grade_text += f"🏫 Классическая оценка: {grade_classic}\n"
                if grade_100:
                    grade_text += f"📊 100-бальная оценка: {grade_100}\n"
                if grade_letter:
                    grade_text += f"🅱️ Буквенная оценка: {grade_letter}\n"
                
                grade_text += f"\n📋 Статус: {status_text}\n"
                
                if is_archived:
                    grade_text += "\n📁 Работа перемещена в архив."
                
                await callback.bot.send_message(
                    chat_id=student.telegram_id,
                    text=grade_text
                )
        except Exception as e:
            logger.error(f"Failed to notify student: {e}")
        
        await callback.message.edit_text(
            f"✅ Оценка сохранена!\n\n"
            f"Работа: {work.title}\n"
            f"Статус: {new_status}\n"
            f"Архив: {'Да' if is_archived else 'Нет'}"
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_grade")
async def cancel_grading(callback: CallbackQuery, state: FSMContext):
    """Отменить оценку"""
    await state.clear()
    await callback.message.edit_text("🚫 Оценка отменена.")
    await callback.answer()
