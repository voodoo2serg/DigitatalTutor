"""
DigitalTutor Telegram Bot
Бот для студентов и преподавателей
"""
import asyncio
import logging
import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import httpx

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TEACHER_ID = os.getenv('TEACHER_TELEGRAM_ID', '')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://backend:8000/api/v1')

# ============================================
# COMMANDS
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    # Check if user exists in system
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/users/{user.id}",
                timeout=10.0
            )
            if response.status_code == 200:
                user_data = response.json()
                await update.message.reply_text(
                    f"👋 С возвращением, {user_data['full_name']}!\n\n"
                    f"📚 Ваша роль: {user_data['role']}\n"
                    f"Группа: {user_data.get('group_name', 'не указана')}\n\n"
                    f"Используйте /help для списка команд."
                )
                return
        except:
            pass
    
    # New user - registration
    keyboard = [
        [InlineKeyboardButton("🎓 Я студент", callback_data='register_student')],
        [InlineKeyboardButton("👨‍🏫 Я преподаватель", callback_data='register_teacher')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👋 Добро пожаловать в DigitalTutor!\n\n"
        f"Я помогу вам управлять учебными проектами, курсовыми, ВКР.\n\n"
        f"Кто вы?",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
📚 <b>Команды DigitalTutor</b>

<b>Для студентов:</b>
/status - Мои работы и статусы
/deadlines - Мои дедлайны
/submit - Сдать работу
/history - История коммуникаций

<b>Для преподавателя:</b>
/admin - Панель управления
/stats - Статистика загрузки
/broadcast - Массовая рассылка

<b>Общие:</b>
/help - Эта справка
/start - Перезапуск бота
    """
    await update.message.reply_text(help_text, parse_mode='HTML')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show student's works status."""
    user = update.effective_user
    
    async with httpx.AsyncClient() as client:
        try:
            # Get user
            response = await client.get(
                f"{API_BASE_URL}/users/{user.id}",
                timeout=10.0
            )
            if response.status_code != 200:
                await update.message.reply_text("❌ Вы не зарегистрированы. Используйте /start")
                return
            
            user_data = response.json()
            
            # Get works
            response = await client.get(
                f"{API_BASE_URL}/works/?student_id={user_data['id']}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                works = response.json()
                
                if not works:
                    await update.message.reply_text("📭 У вас пока нет работ в системе.")
                    return
                
                text = "📚 <b>Ваши работы:</b>\n\n"
                for work in works:
                    status_emoji = {
                        'draft': '📝',
                        'submitted': '📤',
                        'in_review': '🔍',
                        'revision_required': '⚠️',
                        'accepted': '✅',
                        'rejected': '❌'
                    }.get(work['status'], '📄')
                    
                    text += f"{status_emoji} <b>{work['title']}</b>\n"
                    text += f"Статус: {work['status']}\n"
                    if work.get('ai_plagiarism_score'):
                        text += f"Уникальность: {work['ai_plagiarism_score']}%\n"
                    text += "\n"
                
                await update.message.reply_text(text, parse_mode='HTML')
            else:
                await update.message.reply_text("❌ Ошибка получения данных")
        except Exception as e:
            logger.error(f"Error in status: {e}")
            await update.message.reply_text("❌ Ошибка соединения с сервером")

async def submit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit work."""
    await update.message.reply_text(
        "📤 <b>Сдача работы</b>\n\n"
        "Отправьте файл с работой, и я сохраню его в системе.\n"
        "Поддерживаются форматы: PDF, DOCX, TXT",
        parse_mode='HTML'
    )

# ============================================
# MESSAGE HANDLERS
# ============================================

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages."""
    await update.message.reply_text(
        "🎤 Голосовое сообщение получено.\n"
        "Транскрибация голосовых в процессе разработки."
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document uploads."""
    user = update.effective_user
    document = update.message.document
    
    await update.message.reply_text(
        f"📄 Файл получен: {document.file_name}\n"
        f"Размер: {document.file_size} bytes\n\n"
        f"Сохраняю в систему..."
    )
    
    # TODO: Upload to API
    await update.message.reply_text("✅ Файл сохранён!")

# ============================================
# CALLBACK HANDLERS
# ============================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'register_student':
        await query.edit_message_text(
            "🎓 Отлично! Давайте зарегистрируем вас как студента.\n\n"
            "Отправьте ваши данные в формате:\n"
            "<code>ФИО | Группа | Курс</code>\n\n"
            "Пример: <code>Иванов Иван Иванович | ИВТ-101 | 3</code>",
            parse_mode='HTML'
        )
    elif query.data == 'register_teacher':
        await query.edit_message_text(
            "👨‍🏫 Регистрация преподавателя.\n\n"
            "Пожалуйста, свяжитесь с администратором для получения доступа."
        )

# ============================================
# MAIN
# ============================================

def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("submit", submit_command))
    
    # Messages
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Starting DigitalTutor bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
