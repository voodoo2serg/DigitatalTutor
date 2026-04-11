"""
DigitalTutor Bot v2.2 — HOTFIX Регистрация
Экстренный патч для работы регистрации студентов
"""

import logging
import os
from datetime import datetime
from typing import Optional

from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import httpx

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://backend:8000/api/v1')
TEACHER_TELEGRAM_ID = int(os.getenv('TEACHER_TELEGRAM_ID', '0'))

# Состояния регистрации
REG_FIO, REG_GROUP, REG_COURSE, REG_ROLE = range(4)

# Меню
MAIN_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("📋 Мои работы"), KeyboardButton("➕ Сдать работу")],
    [KeyboardButton("📊 Статус"), KeyboardButton("📅 Мой план")],
    [KeyboardButton("💬 Написать руководителю"), KeyboardButton("❓ Помощь")]
], resize_keyboard=True)

MAIN_MENU_TEACHER = ReplyKeyboardMarkup([
    [KeyboardButton("👥 Студенты"), KeyboardButton("📚 Все работы")],
    [KeyboardButton("💬 Сообщения студентов"), KeyboardButton("🌐 Веб-админка")],
    [KeyboardButton("❓ Помощь")]
], resize_keyboard=True)

ROLE_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("🎓 Студент")],
    [KeyboardButton("🎓 Аспирант")],
    [KeyboardButton("❌ Отмена")]
], resize_keyboard=True)

CANCEL_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("❌ Отмена")]
], resize_keyboard=True)

# ============================================
# API ФУНКЦИИ
# ============================================

async def get_user_from_db(telegram_id: int) -> Optional[dict]:
    """Получить пользователя из БД."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE_URL}/users/telegram/{telegram_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None


async def create_user_api(telegram_id: int, username: str, full_name: str, 
                          group_name: str, course: int, role: str) -> Optional[dict]:
    """Создать пользователя через API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/users",
                json={
                    "telegram_id": telegram_id,
                    "telegram_username": username,
                    "full_name": full_name,
                    "group_name": group_name,
                    "course": course,
                    "role": role,
                    "is_active": True
                },
                timeout=10.0
            )
            if response.status_code in [200, 201]:
                logger.info(f"User created: {telegram_id}")
                return response.json()
            else:
                logger.error(f"Failed to create user: {response.status_code} {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None


# ============================================
# РЕГИСТРАЦИЯ (ConversationHandler)
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт бота."""
    user = update.effective_user
    
    # Преподаватель
    if user.id == TEACHER_TELEGRAM_ID:
        await update.message.reply_text(
            f"👋 Добро пожаловать, Преподаватель!",
            reply_markup=MAIN_MENU_TEACHER
        )
        return
    
    # Проверить регистрацию
    user_data = await get_user_from_db(user.id)
    
    if user_data:
        await update.message.reply_text(
            f"👋 С возвращением, {user_data['full_name']}!\n\n"
            f"📚 Роль: {user_data.get('role', '—')}\n"
            f"Группа: {user_data.get('group_name', '—')}",
            reply_markup=MAIN_MENU
        )
    else:
        await update.message.reply_text(
            "👋 Добро пожаловать в DigitalTutor!\n\n"
            "Я помогу вам с учебными работами.\n\n"
            "Давайте познакомимся! Нажмите 📝 Зарегистрироваться",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📝 Зарегистрироваться")]
            ], resize_keyboard=True)
        )


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало регистрации."""
    await update.message.reply_text(
        "📝 Регистрация\n\n"
        "Введите ваше ФИО:\n"
        "(Пример: Иванов Иван Иванович)",
        reply_markup=CANCEL_MENU
    )
    return REG_FIO


async def register_fio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение ФИО."""
    text = update.message.text
    
    if text == "❌ Отмена":
        await update.message.reply_text("Регистрация отменена.", reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📝 Зарегистрироваться")]
        ], resize_keyboard=True))
        return ConversationHandler.END
    
    context.user_data['fio'] = text
    await update.message.reply_text(
        "📚 Введите номер группы:\n"
        "(Пример: ИС-2024-1)",
        reply_markup=CANCEL_MENU
    )
    return REG_GROUP


async def register_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение группы."""
    text = update.message.text
    
    if text == "❌ Отмена":
        await update.message.reply_text("Регистрация отменена.", reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📝 Зарегистрироваться")]
        ], resize_keyboard=True))
        return ConversationHandler.END
    
    context.user_data['group'] = text
    await update.message.reply_text(
        "📅 Введите курс (цифрой):\n"
        "(1, 2, 3, 4, 5, 6)",
        reply_markup=CANCEL_MENU
    )
    return REG_COURSE


async def register_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение курса."""
    text = update.message.text
    
    if text == "❌ Отмена":
        await update.message.reply_text("Регистрация отменена.", reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📝 Зарегистрироваться")]
        ], resize_keyboard=True))
        return ConversationHandler.END
    
    if not text.isdigit() or int(text) not in range(1, 7):
        await update.message.reply_text(
            "⚠️ Введите курс цифрой от 1 до 6",
            reply_markup=CANCEL_MENU
        )
        return REG_COURSE
    
    context.user_data['course'] = int(text)
    await update.message.reply_text(
        "🎓 Выберите вашу роль:",
        reply_markup=ROLE_MENU
    )
    return REG_ROLE


async def register_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение роли и завершение регистрации."""
    text = update.message.text
    
    if text == "❌ Отмена":
        await update.message.reply_text("Регистрация отменена.", reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📝 Зарегистрироваться")]
        ], resize_keyboard=True))
        return ConversationHandler.END
    
    # Определяем роль
    if "Студент" in text:
        role = "student"
    elif "Аспирант" in text:
        role = "graduate_student"
    else:
        role = "student"
    
    # Сохраняем
    user = update.effective_user
    
    result = await create_user_api(
        telegram_id=user.id,
        username=user.username or "",
        full_name=context.user_data['fio'],
        group_name=context.user_data['group'],
        course=context.user_data['course'],
        role=role
    )
    
    if result:
        await update.message.reply_text(
            f"✅ Регистрация завершена!\n\n"
            f"👤 {context.user_data['fio']}\n"
            f"📚 Группа: {context.user_data['group']}\n"
            f"📅 Курс: {context.user_data['course']}\n"
            f"🎓 Роль: {text}\n\n"
            f"Добро пожаловать! Теперь вы можете пользоваться ботом.",
            reply_markup=MAIN_MENU
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка регистрации. Попробуйте позже или обратитесь к преподавателю.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📝 Зарегистрироваться")]
            ], resize_keyboard=True)
        )
    
    return ConversationHandler.END


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации."""
    await update.message.reply_text(
        "Регистрация отменена.",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("📝 Зарегистрироваться")]
        ], resize_keyboard=True)
    )
    return ConversationHandler.END


# ============================================
# ОБРАБОТКА ТЕКСТА
# ============================================

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений."""
    user = update.effective_user
    text = update.message.text
    
    # Преподаватель
    if user.id == TEACHER_TELEGRAM_ID:
        await update.message.reply_text(
            "Используйте меню для навигации.",
            reply_markup=MAIN_MENU_TEACHER
        )
        return
    
    # Проверка регистрации
    user_data = await get_user_from_db(user.id)
    if not user_data and text != "📝 Зарегистрироваться":
        await update.message.reply_text(
            "⚠️ Вы не зарегистрированы. Нажмите 📝 Зарегистрироваться",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📝 Зарегистрироваться")]
            ], resize_keyboard=True)
        )
        return
    
    # Обработка меню
    if text == "📋 Мои работы":
        await update.message.reply_text("📭 Список работ в разработке", reply_markup=MAIN_MENU)
    elif text == "➕ Сдать работу":
        await update.message.reply_text("📤 Функция сдачи работы в разработке", reply_markup=MAIN_MENU)
    elif text == "📊 Статус":
        await update.message.reply_text("📊 Проверка статуса в разработке", reply_markup=MAIN_MENU)
    elif text == "📅 Мой план":
        await update.message.reply_text("📅 План работы в разработке", reply_markup=MAIN_MENU)
    elif text == "💬 Написать руководителю":
        await update.message.reply_text("✍️ Отправка сообщения в разработке", reply_markup=MAIN_MENU)
    elif text == "❓ Помощь":
        await update.message.reply_text(
            "📚 Помощь:\n\n"
            "• 📋 Мои работы - список работ\n"
            "• ➕ Сдать работу - загрузить работу\n"
            "• 💬 Написать руководителю - связь",
            reply_markup=MAIN_MENU
        )
    else:
        await update.message.reply_text("Используйте меню для навигации.", reply_markup=MAIN_MENU)


# ============================================
# MAIN
# ============================================

def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    logger.info("DigitalTutor bot v2.2 (HOTFIX) starting...")
    logger.info(f"API_BASE_URL: {API_BASE_URL}")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для регистрации
    registration_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(📝 Зарегистрироваться)$"), register_start)],
        states={
            REG_FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_fio)],
            REG_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_group)],
            REG_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_course)],
            REG_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_role)],
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)],
    )
    
    # Хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(registration_conv)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
