"""
DigitalTutor Bot - Plan Handler
План работы для разных ролей
"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from bot.keyboards import get_main_menu
from bot.templates.messages import Messages

logger = logging.getLogger(__name__)
router = Router()


STUDENT_ROLES = {
    "vkr": {
        "name": "ВКР",
        "plan_points": [
            {"num": 1, "name": "Предзащита", "description": "Предварительная защита работы"},
            {"num": 2, "name": "Финальная защита", "description": "Окончательная защита ВКР"}
        ]
    },
    "aspirant": {
        "name": "Аспирант",
        "plan_points": [
            {"num": 1, "name": "Вступительные экзамены", "description": "Сдача вступительных экзаменов"},
            {"num": 2, "name": "Индивидуальный план", "description": "Утверждение индивидуального плана"},
            {"num": 3, "name": "Кандидатский минимум", "description": "Сдача кандидатского минимума"},
            {"num": 4, "name": "Публикации", "description": "Публикация научных статей"},
            {"num": 5, "name": "Аспирантский доклад", "description": "Доклад на кафедре"},
            {"num": 6, "name": "Кандидатская диссертация", "description": "Подготовка и защита диссертации"}
        ]
    },
    "vkr_article": {
        "name": "ВКР + Статья",
        "plan_points": [
            {"num": 1, "name": "Научная статья", "description": "Написание и публикация статьи"},
            {"num": 2, "name": "Текст ВКР", "description": "Подготовка текста ВКР"},
            {"num": 3, "name": "Защита", "description": "Предзащита и финальная защита"}
        ]
    },
    "article_guide": {
        "name": "Руководство по статье",
        "plan_points": [
            {"num": 1, "name": "Выбор темы", "description": "Определение темы и журнала"},
            {"num": 2, "name": "Написание", "description": "Подготовка текста статьи"},
            {"num": 3, "name": "Публикация", "description": "Отправка в журнал, рецензирование"}
        ]
    },
    "work_guide": {
        "name": "Руководство по работе",
        "plan_points": [
            {"num": 1, "name": "Тема и план", "description": "Утверждение темы и плана работы"},
            {"num": 2, "name": "Написание", "description": "Работа над текстом"},
            {"num": 3, "name": "Завершение", "description": "Финальная проверка и сдача"}
        ]
    },
    "other": {
        "name": "Другой проект",
        "plan_points": [
            {"num": 1, "name": "Постановка задачи", "description": "Определение целей и задач"},
            {"num": 2, "name": "Выполнение", "description": "Работа над проектом"},
            {"num": 3, "name": "Результат", "description": "Подготовка итогового результата"}
        ]
    }
}


@router.message(F.text == "📅 Мой план")
async def show_my_plan(message: Message):
    """Показать план работ для текущей роли"""
    telegram_id = message.from_user.id
    
    from bot.models import AsyncSessionContext, User
    
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
        
        # Определяем роль
        role_code = None
        for code, info in STUDENT_ROLES.items():
            if info['name'] == user.role:
                role_code = code
                break
        
        if not role_code:
            role_code = "other"
        
        role_info = STUDENT_ROLES.get(role_code, STUDENT_ROLES['other'])
        
        text = Messages.PLAN_HEADER.format(role=role_info['name'])
        
        for point in role_info['plan_points']:
            text += Messages.PLAN_POINT.format(
                num=point['num'],
                name=point['name'],
                description=point['description']
            )
        
        text += "\n<i>Выполняйте работы поэтапно. После завершения каждого этапа — сдавайте результат через «➕ Сдать работу»</i>"
        
        await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")
