"""
DigitalTutor Bot - Plan Handler (Обновлённый)
План работы с двумя блоками: текущие задачи + установка дедлайнов
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from datetime import datetime, timedelta

from bot.keyboards import get_main_menu

logger = logging.getLogger(__name__)
router = Router()

# Структура работ по типам (в месяцах)
WORK_TIMELINES = {
    "article": {
        "name": "📄 Научная статья",
        "duration_months": 3,
        "phases": [
            {"name": "Утверждение плана", "duration_weeks": 2, "order": 1},
            {"name": "Написание основы текста", "duration_weeks": 4, "order": 2},
            {"name": "Корректировки", "duration_weeks": 3, "order": 3},
            {"name": "Проверка на антиплагиат", "duration_weeks": 1, "order": 4},
            {"name": "Согласование для публикации", "duration_weeks": 2, "order": 5},
        ],
        "final_button": "✅ Согласовано для публикации"
    },
    "coursework": {
        "name": "📚 Курсовая работа",
        "duration_months": 5,
        "phases": [
            {"name": "Утверждение плана", "duration_weeks": 2, "order": 1},
            {"name": "Написание основы текста", "duration_weeks": 8, "order": 2},
            {"name": "Корректировки", "duration_weeks": 6, "order": 3},
            {"name": "Проверка на антиплагиат", "duration_weeks": 2, "order": 4},
            {"name": "Допущено к защите", "duration_weeks": 2, "order": 5},
        ],
        "final_button": "✅ Допущено к защите"
    },
    "vkr": {
        "name": "🎓 ВКР (Бакалавр/Магистр)",
        "duration_months": 5,
        "phases": [
            {"name": "Утверждение плана", "duration_weeks": 2, "order": 1},
            {"name": "Написание основы текста", "duration_weeks": 10, "order": 2},
            {"name": "Корректировки", "duration_weeks": 6, "order": 3},
            {"name": "Проверка на антиплагиат", "duration_weeks": 2, "order": 4},
            {"name": "Допущено к защите", "duration_weeks": 2, "order": 5},
        ],
        "final_button": "✅ Допущено к защите"
    }
}


def calculate_phase_dates(start_date, phases):
    """Рассчитать даты для каждой фазы"""
    current_date = start_date
    result = []
    
    for phase in phases:
        end_date = current_date + timedelta(weeks=phase["duration_weeks"])
        result.append({
            "name": phase["name"],
            "start": current_date,
            "end": end_date,
            "order": phase["order"]
        })
        current_date = end_date
    
    return result


def get_status_emoji(phase_end, now):
    """Определить статус фазы"""
    if now > phase_end:
        return "✅"  # Завершено
    elif (phase_end - now).days <= 7:
        return "🔄"  # В работе / скоро дедлайн
    else:
        return "⭕"  # Ожидает


@router.message(F.text == "📅 Мой план")
async def show_my_plan(message: Message):
    """Показать план работы с двумя блоками"""
    telegram_id = message.from_user.id
    
    from bot.models import AsyncSessionContext, User, StudentWork
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                "❌ Сначала завершите регистрацию с помощью /start",
                reply_markup=get_main_menu()
            )
            return
        
        # Получаем работы студента
        result = await session.execute(
            select(StudentWork).where(StudentWork.student_id == user.id)
        )
        works = result.scalars().all()
        
        now = datetime.utcnow()
        
        # ═══════════════════════════════════════════════════════════
        # БЛОК 1: ТЕКУЩИЕ ЗАДАЧИ С УСТАНОВЛЕННЫМИ ДЕДЛАЙНАМИ
        # ═══════════════════════════════════════════════════════════
        text = "📅 <b>МОЙ ПЛАН РАБОТЫ</b>\n\n"
        text += "━" * 30 + "\n"
        text += "<b>📋 БЛОК 1: ТЕКУЩИЕ ЗАДАЧИ</b>\n"
        text += "━" * 30 + "\n\n"
        
        # Активные работы с дедлайнами
        active_works = [w for w in works if w.deadline and w.status not in ['accepted', 'rejected']]
        
        if active_works:
            # Сортируем по дедлайну (ближайшие первыми)
            active_works.sort(key=lambda x: x.deadline)
            
            for work in active_works:
                days_left = (work.deadline - now).days
                
                if days_left < 0:
                    emoji = "🔴"
                    status = f"Просрочено на {abs(days_left)} дн."
                elif days_left <= 3:
                    emoji = "🚨"
                    status = f"Осталось {days_left} дн."
                elif days_left <= 7:
                    emoji = "⚠️"
                    status = f"Осталось {days_left} дн."
                else:
                    emoji = "📅"
                    status = f"Осталось {days_left} дн."
                
                text += f"{emoji} <b>{work.work_type or 'Работа'}</b>\n"
                text += f"   Тема: {work.title[:40]}...\n"
                text += f"   Дедлайн: {work.deadline.strftime('%d.%m.%Y')} — {status}\n"
                text += f"   Статус: {get_status_text(work.status)}\n\n"
        else:
            text += "<i>Нет активных задач с установленными дедлайнами.\n"
            text += "Создайте новую работу через «➕ Сдать работу»</i>\n\n"
        
        # ═══════════════════════════════════════════════════════════
        # БЛОК 2: ПРЕДЛОЖЕНИЕ УСТАНОВИТЬ ДЕДЛАЙНЫ
        # ═══════════════════════════════════════════════════════════
        text += "━" * 30 + "\n"
        text += "<b>📊 БЛОК 2: ПЛАНИРОВАНИЕ НОВЫХ РАБОТ</b>\n"
        text += "━" * 30 + "\n\n"
        
        text += "Выберите тип работы для планирования:\n\n"
        
        # Работы без дедлайнов (черновики)
        draft_works = [w for w in works if not w.deadline and w.status == 'draft']
        
        if draft_works:
            text += "<b>📝 Работы без дедлайна:</b>\n"
            for work in draft_works:
                text += f"   • {work.work_type or 'Работа'}: {work.title[:30]}...\n"
            text += "\n"
        
        # Предлагаем структуру планирования
        text += "<b>📅 Рекомендуемые сроки:</b>\n\n"
        
        for work_type, info in WORK_TIMELINES.items():
            text += f"{info['name']} — <b>{info['duration_months']} мес.</b>\n"
            text += "   Этапы:\n"
            
            for phase in info['phases']:
                text += f"   {phase['order']}. {phase['name']} — {phase['duration_weeks']} нед.\n"
            
            text += f"   <i>Финал: {info['final_button']}</i>\n\n"
        
        # Кнопки действий
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать новую работу", callback_data="create_work")],
            [InlineKeyboardButton(text="📋 Мои работы", callback_data="my_works")],
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


def get_status_text(status):
    """Получить текст статуса"""
    status_map = {
        "draft": "📝 Черновик",
        "submitted": "📤 Отправлена",
        "in_review": "👀 На проверке",
        "revision_required": "🔄 Требует доработки",
        "accepted": "✅ Принята",
        "rejected": "❌ Отклонена",
    }
    return status_map.get(status, status)
