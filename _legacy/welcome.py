#!/usr/bin/env python3
"""
DigitalTutor - Скрипт первого входа студента

Этот модуль обрабатывает первый вход студента в систему через Telegram.
Включает:
- Приветствие от преподавателя
- Сбор ФИО и группы
- Выбор типа работы
- Установку темы и дедлайнов
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler, 
        CallbackQueryHandler, ContextTypes, filters
    )
except ImportError:
    print("Установите python-telegram-bot: pip install python-telegram-bot")
    sys.exit(1)

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TEACHER_NAME = os.getenv("TEACHER_NAME", "Водопетов С.В.")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://teacher:password@localhost:5432/teaching")

# Сообщения
MESSAGES = {
    "welcome": f"""👋 Привет!

Я {TEACHER_NAME}. Вероятно у нас с вами идет научная или проектная работа! 

Для того, чтобы упростить наше взаимодействие я сделал этого бота, который сильно облегчит нашу коммуникацию и сделает так, чтобы ничего не потерялось!

Прошу потратить немного времени на первую регистрацию в системе и ознакомится с /help.

Хорошего дня! 🎓""",

    "request_name": "📝 Введите ваше ФИО полностью:",
    
    "request_group": "📚 Введите вашу группу:",
    
    "select_work_type": "🎓 Выберите тип работы:",
    
    "request_topic": "📖 Напишите тему вашей работы (если уже есть).\nЕсли темы пока нет, напишите '-' :",
    
    "registration_complete": """✅ Регистрация завершена!

📋 Ваши данные:
• ФИО: {name}
• Группа: {group}
• Тип работы: {work_type}
• Тема: {topic}

📅 Ближайший milestone: {first_milestone}
📆 Дедлайн: {first_deadline}

Для просмотра своих работ: /status
Для справки: /help
""",
    
    "already_registered": """Вы уже зарегистрированы!

📋 Ваши данные:
• ФИО: {name}
• Группа: {group}

Для изменения данных обратитесь к преподавателю.""",
    
    "help": """📚 Справка по командам DigitalTutor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ОСНОВНЫЕ КОМАНДЫ:

/start - Регистрация в системе
/status - Мои работы и статусы
/deadlines - Мои дедлайны
/submit - Сдать работу
/history - История коммуникаций

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 РАБОТА С ФАЙЛАМИ:

Просто отправьте файл боту, и он будет привязан к вашей текущей работе.
Поддерживаемые форматы: .docx, .pdf, .pptx, .zip

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❓ ЕСТЬ ВОПРОСЫ?

Напишите ваш вопрос прямо в чат, и я передам его преподавателю.
"""
}

# Типы работ и их milestone'ы
WORK_TYPES = {
    "coursework": {
        "name": "Курсовая работа",
        "milestones": [
            {"name": "Выбор темы", "days": 14},
            {"name": "План работы", "days": 21},
            {"name": "Черновик", "days": 45},
            {"name": "Финальная версия", "days": 60}
        ]
    },
    "thesis": {
        "name": "ВКР (диплом)",
        "milestones": [
            {"name": "Выбор темы", "days": 21},
            {"name": "Глава 1", "days": 45},
            {"name": "Глава 2", "days": 70},
            {"name": "Глава 3", "days": 90},
            {"name": "Полный текст", "days": 105},
            {"name": "Предзащита", "days": 115},
            {"name": "Финальная версия", "days": 125}
        ]
    },
    "article": {
        "name": "Научная статья",
        "milestones": [
            {"name": "Выбор темы", "days": 7},
            {"name": "Текст статьи", "days": 30},
            {"name": "Рецензирование", "days": 45},
            {"name": "Публикация", "days": 60}
        ]
    },
    "project": {
        "name": "Проектная работа",
        "milestones": [
            {"name": "Сценарий", "days": 14},
            {"name": "Реализация", "days": 45},
            {"name": "Тестирование", "days": 55},
            {"name": "Релиз", "days": 60}
        ]
    },
    "phd": {
        "name": "Аспирантура",
        "milestones": [
            {"name": "Статья 1", "days": 90},
            {"name": "Статья 2", "days": 180},
            {"name": "Статья 3", "days": 270},
            {"name": "Диссертация", "days": 365}
        ]
    }
}

# =============================================================================
# СОСТОЯНИЯ РЕГИСТРАЦИИ
# =============================================================================

class RegistrationState:
    """Состояния процесса регистрации"""
    START = "start"
    WAITING_NAME = "waiting_name"
    WAITING_GROUP = "waiting_group"
    WAITING_WORK_TYPE = "waiting_work_type"
    WAITING_TOPIC = "waiting_topic"
    COMPLETED = "completed"

# Хранилище состояний (в продакшене использовать Redis)
user_states: Dict[int, Dict[str, Any]] = {}

# =============================================================================
# ОБРАБОТЧИКИ КОМАНД
# =============================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Проверяем, зарегистрирован ли пользователь
    existing_user = await get_user_from_db(user_id)
    
    if existing_user:
        await update.message.reply_text(
            MESSAGES["already_registered"].format(
                name=existing_user.get("name", "Не указано"),
                group=existing_user.get("group_name", "Не указано")
            )
        )
        return
    
    # Начинаем регистрацию
    user_states[user_id] = {
        "state": RegistrationState.WAITING_NAME,
        "data": {}
    }
    
    await update.message.reply_text(MESSAGES["welcome"])
    await update.message.reply_text(MESSAGES["request_name"])

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(MESSAGES["help"])

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    user_id = update.effective_user.id
    
    # Получаем работы пользователя из БД
    submissions = await get_user_submissions(user_id)
    
    if not submissions:
        await update.message.reply_text(
            "📭 У вас пока нет активных работ.\n"
            "Для регистрации новой работы используйте /start"
        )
        return
    
    # Формируем сообщение
    message = "📋 Ваши работы:\n\n"
    
    for sub in submissions:
        status_emoji = {
            "draft": "📝",
            "submitted": "📤",
            "reviewing": "🔍",
            "revision": "🔄",
            "approved": "✅",
            "rejected": "❌"
        }.get(sub.get("status", "draft"), "📄")
        
        message += f"""{status_emoji} {sub.get('title', 'Без названия')}
   📁 Тип: {WORK_TYPES.get(sub.get('type', ''), {}).get('name', sub.get('type'))}
   📊 Статус: {sub.get('status', 'draft')}
   📅 Дедлайн: {sub.get('deadline', 'Не указан')}
   📌 Этап: {sub.get('current_milestone', '-')}

"""
    
    await update.message.reply_text(message)

async def cmd_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /deadlines"""
    user_id = update.effective_user.id
    
    deadlines = await get_user_deadlines(user_id)
    
    if not deadlines:
        await update.message.reply_text("🎉 У вас нет ближайших дедлайнов!")
        return
    
    message = "📅 Ваши дедлайны:\n\n"
    
    today = datetime.now().date()
    
    for dl in deadlines:
        deadline_date = datetime.strptime(dl["deadline"], "%Y-%m-%d").date()
        days_left = (deadline_date - today).days
        
        if days_left < 0:
            emoji = "🔴"
            status = f"Просрочен на {abs(days_left)} дн."
        elif days_left == 0:
            emoji = "🔴"
            status = "СЕГОДНЯ!"
        elif days_left <= 3:
            emoji = "🟡"
            status = f"{days_left} дн."
        else:
            emoji = "🟢"
            status = f"{days_left} дн."
        
        message += f"""{emoji} {dl['title']}
   📆 {dl['deadline']} ({status})
   📌 {dl['milestone']}

"""
    
    await update.message.reply_text(message)

# =============================================================================
# ОБРАБОТЧИКИ СООБЩЕНИЙ
# =============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Если пользователь не в процессе регистрации
    if user_id not in user_states:
        # Сохраняем сообщение в историю коммуникаций
        await save_communication(user_id, text, direction="in")
        
        await update.message.reply_text(
            "✅ Ваше сообщение получено и сохранено.\n"
            "Преподаватель увидит его в ближайшее время."
        )
        return
    
    state_data = user_states[user_id]
    current_state = state_data["state"]
    
    if current_state == RegistrationState.WAITING_NAME:
        state_data["data"]["name"] = text
        state_data["state"] = RegistrationState.WAITING_GROUP
        await update.message.reply_text(MESSAGES["request_group"])
    
    elif current_state == RegistrationState.WAITING_GROUP:
        state_data["data"]["group_name"] = text
        state_data["state"] = RegistrationState.WAITING_WORK_TYPE
        
        # Создаём клавиатуру с типами работ
        keyboard = []
        for code, info in WORK_TYPES.items():
            keyboard.append([
                InlineKeyboardButton(info["name"], callback_data=f"type:{code}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            MESSAGES["select_work_type"],
            reply_markup=reply_markup
        )
    
    elif current_state == RegistrationState.WAITING_TOPIC:
        topic = text if text != "-" else "Не указана"
        state_data["data"]["topic"] = topic
        
        # Завершаем регистрацию
        await complete_registration(update, context, user_id, state_data["data"])

# =============================================================================
# ОБРАБОТЧИКИ CALLBACK
# =============================================================================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if user_id not in user_states:
        return
    
    state_data = user_states[user_id]
    
    if data.startswith("type:"):
        work_type = data.split(":")[1]
        state_data["data"]["work_type"] = work_type
        state_data["data"]["work_type_name"] = WORK_TYPES[work_type]["name"]
        state_data["state"] = RegistrationState.WAITING_TOPIC
        
        await query.message.edit_text(
            f"✅ Выбрано: {WORK_TYPES[work_type]['name']}\n\n"
            f"{MESSAGES['request_topic']}"
        )

# =============================================================================
# ФУНКЦИИ РЕГИСТРАЦИИ
# =============================================================================

async def complete_registration(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    data: Dict[str, Any]
):
    """Завершение регистрации и сохранение в БД"""
    
    work_type = data.get("work_type", "coursework")
    milestones = WORK_TYPES[work_type]["milestones"]
    first_milestone = milestones[0]["name"]
    first_deadline = (datetime.now() + timedelta(days=milestones[0]["days"])).strftime("%d.%m.%Y")
    
    # Сохраняем в БД
    await save_user_to_db(user_id, data)
    
    # Создаём submission
    submission_id = await create_submission(user_id, work_type, data.get("topic", ""))
    
    # Очищаем состояние
    if user_id in user_states:
        del user_states[user_id]
    
    # Отправляем подтверждение
    await update.message.reply_text(
        MESSAGES["registration_complete"].format(
            name=data.get("name", "Не указано"),
            group=data.get("group_name", "Не указано"),
            work_type=data.get("work_type_name", work_type),
            topic=data.get("topic", "Не указана"),
            first_milestone=first_milestone,
            first_deadline=first_deadline
        )
    )

# =============================================================================
# ФУНКЦИИ БАЗЫ ДАННЫХ (заглушки)
# =============================================================================

async def get_user_from_db(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение пользователя из БД"""
    # TODO: Реализовать реальный запрос к БД
    # Заглушка для демонстрации
    return None

async def save_user_to_db(user_id: int, data: Dict[str, Any]) -> bool:
    """Сохранение пользователя в БД"""
    # TODO: Реализовать реальное сохранение в БД
    logging.info(f"Saving user {user_id}: {data}")
    return True

async def create_submission(user_id: int, work_type: str, topic: str) -> str:
    """Создание submission в БД"""
    # TODO: Реализовать реальное создание
    import uuid
    return str(uuid.uuid4())

async def get_user_submissions(user_id: int) -> list:
    """Получение работ пользователя"""
    # TODO: Реализовать реальный запрос
    return []

async def get_user_deadlines(user_id: int) -> list:
    """Получение дедлайнов пользователя"""
    # TODO: Реализовать реальный запрос
    return []

async def save_communication(user_id: int, message: str, direction: str = "in"):
    """Сохранение коммуникации в БД"""
    logging.info(f"Communication from {user_id}: {message[:50]}...")
    return True

# =============================================================================
# ЗАПУСК БОТА
# =============================================================================

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        print("Ошибка: Установите переменную TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("deadlines", cmd_deadlines))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем
    print("🤖 DigitalTutor Bot запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
