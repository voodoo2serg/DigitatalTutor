"""
DigitalTutor Bot v2.3 — Work Submission Module
Добавлена полноценная сдача работ
"""
import logging
import httpx
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
from uuid import uuid4
from datetime import datetime

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Config
API_BASE_URL = "http://digitatal-backend:8000/api/v1"

# Conversation states
WORK_TYPE, WORK_TITLE, WORK_FILE, WORK_CONFIRM = range(4)

# Main menu
MAIN_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("📋 Мои работы"), KeyboardButton("➕ Сдать работу")],
    [KeyboardButton("📊 Статус"), KeyboardButton("💬 Написать руководителю")],
    [KeyboardButton("❓ Помощь")]
], resize_keyboard=True)

# Work types mapping
WORK_TYPES = {
    "1": ("3e981ca3-704a-4d2f-af81-c17aefa8ecf4", "Курсовая работа"),
    "2": ("8be99b51-0960-49c4-8ac2-436143fe7290", "ВКР (Бакалавр)"),
    "3": ("130a0263-60a6-4f70-bd0c-39fcbfa28bb7", "ВКР (Магистр)"),
    "4": ("75be7f1a-b20c-4724-b4a3-4ea76434c63f", "Научная статья"),
    "5": ("3e5b6a88-f9d2-4b36-a51f-8ec47846890f", "Реферат"),
    "6": ("093bc1c3-3a4d-49a0-8a12-7c1483a6bd45", "Проект"),
    "7": ("d3e57c9e-ea11-44d0-bfd6-97b1b04a1482", "Другое")
}


async def get_or_create_user(telegram_id: int, username: str, full_name: str):
    """Get existing user or create new one"""
    async with httpx.AsyncClient() as client:
        # Check if user exists
        response = await client.get(
            f"{API_BASE_URL}/users/telegram/{telegram_id}",
            timeout=30.0
        )
        
        if response.status_code == 200:
            return response.json()
        
        # Create new user
        response = await client.post(
            f"{API_BASE_URL}/users/",
            json={
                "telegram_id": telegram_id,
                "username": username or str(telegram_id),
                "full_name": full_name or f"Student_{telegram_id}",
                "role": "student"
            },
            timeout=30.0
        )
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"Failed to create user: {response.status_code} - {response.text}")
            return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - register user and show menu"""
    user = update.effective_user
    
    await update.message.reply_text(
        "🔄 Регистрация в системе..."
    )
    
    db_user = await get_or_create_user(
        user.id,
        user.username,
        user.full_name
    )
    
    if db_user:
        await update.message.reply_text(
            f"✅ Добро пожаловать, {user.full_name or user.username}!\n\n"
            f"Вы зарегистрированы в системе DigitalTutor.\n\n"
            f"📋 Доступные функции:\n"
            f"• Мои работы — просмотр статуса\n"
            f"• Сдать работу — загрузить файл\n"
            f"• Написать руководителю — связь",
            reply_markup=MAIN_MENU
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка регистрации. Попробуйте позже."
        )


async def list_my_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's works"""
    user = update.effective_user
    
    await update.message.reply_text("🔄 Загрузка списка работ...")
    
    # Get user from DB
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            f"{API_BASE_URL}/users/telegram/{user.id}",
            timeout=30.0
        )
        
        if user_resp.status_code != 200:
            await update.message.reply_text(
                "❌ Вы не зарегистрированы. Нажмите /start",
                reply_markup=MAIN_MENU
            )
            return
        
        user_data = user_resp.json()
        user_id = user_data.get("id")
        
        # Get works
        works_resp = await client.get(
            f"{API_BASE_URL}/works/?student_id={user_id}",
            timeout=30.0
        )
        
        if works_resp.status_code == 200:
            works = works_resp.json()
            
            if not works:
                await update.message.reply_text(
                    "📭 У вас пока нет работ в системе.\n\n"
                    "Нажмите «➕ Сдать работу» чтобы добавить.",
                    reply_markup=MAIN_MENU
                )
                return
            
            message = "📋 Ваши работы:\n\n"
            for w in works:
                status_emoji = {
                    "draft": "📝",
                    "submitted": "📤",
                    "in_review": "👀",
                    "revision": "🔄",
                    "accepted": "✅",
                    "rejected": "❌"
                }.get(w.get("status"), "❓")
                
                message += f"{status_emoji} {w.get('title', 'Без названия')}\n"
                message += f"   Статус: {w.get('status', 'unknown')}\n"
                if w.get('ai_plagiarism_score') is not None:
                    message += f"   Плагиат ИИ: {w['ai_plagiarism_score']:.1%}\n"
                message += "\n"
            
            await update.message.reply_text(message, reply_markup=MAIN_MENU)
        else:
            await update.message.reply_text(
                "❌ Не удалось загрузить работы",
                reply_markup=MAIN_MENU
            )


# ==================== WORK SUBMISSION FLOW ====================

async def submit_work_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start work submission flow"""
    user = update.effective_user
    
    # Verify user exists
    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            f"{API_BASE_URL}/users/telegram/{user.id}",
            timeout=30.0
        )
        
        if user_resp.status_code != 200:
            await update.message.reply_text(
                "❌ Сначала зарегистрируйтесь: /start"
            )
            return ConversationHandler.END
        
        context.user_data["student_id"] = user_resp.json().get("id")
    
    # Show work types
    keyboard = [
        [InlineKeyboardButton("1. Курсовая работа", callback_data="1")],
        [InlineKeyboardButton("2. ВКР (Бакалавр)", callback_data="2")],
        [InlineKeyboardButton("3. ВКР (Магистр)", callback_data="3")],
        [InlineKeyboardButton("4. Научная статья", callback_data="4")],
        [InlineKeyboardButton("5. Реферат", callback_data="5")],
        [InlineKeyboardButton("6. Проект", callback_data="6")],
        [InlineKeyboardButton("7. Другое", callback_data="7")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    
    await update.message.reply_text(
        "📚 Выберите тип работы:\n\n"
        "1 — Курсовая работа\n"
        "2 — ВКР (Бакалавр)\n"
        "3 — ВКР (Магистр)\n"
        "4 — Научная статья\n"
        "5 — Реферат\n"
        "6 — Проект\n"
        "7 — Другое",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return WORK_TYPE


async def work_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle work type selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Отменено")
        await query.message.reply_text("Главное меню:", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    
    type_id, type_name = WORK_TYPES.get(query.data, (None, "Другое"))
    context.user_data["work_type_id"] = type_id
    context.user_data["work_type_name"] = type_name
    
    await query.edit_message_text(
        f"✅ Выбрано: {type_name}\n\n"
        f"📝 Теперь введите название работы:\n"
        f"(тема, предмет, краткое описание)"
    )
    
    return WORK_TITLE


async def work_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle work title"""
    title = update.message.text.strip()
    
    if len(title) < 5:
        await update.message.reply_text(
            "❌ Название слишком короткое (минимум 5 символов).\n"
            "Попробуйте ещё раз:"
        )
        return WORK_TITLE
    
    context.user_data["work_title"] = title
    
    await update.message.reply_text(
        f"✅ Название: {title}\n\n"
        f"📎 Теперь отправьте файл работы:\n"
        f"Поддерживаются: PDF, DOC, DOCX, TXT\n\n"
        f"Или отправьте /skip чтобы пропустить загрузку файла"
    )
    
    return WORK_FILE


async def work_file_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file upload"""
    # Check if document
    if not update.message.document:
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте файл (PDF, DOC, DOCX)\n"
            "Или используйте /skip чтобы пропустить"
        )
        return WORK_FILE
    
    document = update.message.document
    
    # Check file size (max 20MB)
    if document.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            "❌ Файл слишком большой (максимум 20MB)"
        )
        return WORK_FILE
    
    # Check file type
    allowed_types = ['application/pdf', 'application/msword', 
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     'text/plain']
    
    if document.mime_type not in allowed_types:
        await update.message.reply_text(
            "❌ Неподдерживаемый формат.\n"
            "Разрешены: PDF, DOC, DOCX, TXT"
        )
        return WORK_FILE
    
    # Store file info
    context.user_data["file"] = {
        "file_id": document.file_id,
        "filename": document.file_name,
        "mime_type": document.mime_type,
        "size": document.file_size
    }
    
    # Show confirmation
    await show_confirmation(update, context)
    return WORK_CONFIRM


async def skip_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skip file upload"""
    context.user_data["file"] = None
    await show_confirmation(update, context)
    return WORK_CONFIRM


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show work submission confirmation"""
    work_type = context.user_data.get("work_type_name", "Другое")
    title = context.user_data.get("work_title", "Без названия")
    file_info = context.user_data.get("file")
    
    message = f"📋 Проверьте данные:\n\n"
    message += f"📚 Тип: {work_type}\n"
    message += f"📝 Название: {title}\n"
    
    if file_info:
        message += f"📎 Файл: {file_info['filename']}\n"
        message += f"   Размер: {file_info['size'] / 1024:.1f} KB\n"
    else:
        message += "📎 Файл: не загружен\n"
    
    message += f"\n✅ Всё верно?"
    
    keyboard = [
        [InlineKeyboardButton("✅ Отправить", callback_data="confirm")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def confirm_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Submit work to backend"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Отменено")
        await query.message.reply_text("Главное меню:", reply_markup=MAIN_MENU)
        context.user_data.clear()
        return ConversationHandler.END
    
    await query.edit_message_text("🔄 Сохранение работы...")
    
    # Create work in database
    student_id = context.user_data.get("student_id")
    work_type_id = context.user_data.get("work_type_id")
    title = context.user_data.get("work_title")
    file_info = context.user_data.get("file")
    
    try:
        async with httpx.AsyncClient() as client:
            # Create work
            work_data = {
                "student_id": student_id,
                "work_type_id": work_type_id,
                "title": title,
                "status": "submitted",
                "submission_date": datetime.utcnow().isoformat()
            }
            
            work_resp = await client.post(
                f"{API_BASE_URL}/works/",
                json=work_data,
                timeout=30.0
            )
            
            if work_resp.status_code not in [200, 201]:
                logger.error(f"Failed to create work: {work_resp.text}")
                await query.message.reply_text(
                    "❌ Ошибка при сохранении работы. Попробуйте позже.",
                    reply_markup=MAIN_MENU
                )
                return ConversationHandler.END
            
            work = work_resp.json()
            work_id = work.get("id")
            
            # Upload file if provided
            if file_info and work_id:
                await query.edit_message_text("🔄 Загрузка файла...")
                
                # Download file from Telegram
                file_obj = await context.bot.get_file(file_info["file_id"])
                file_bytes = await file_obj.download_as_bytearray()
                
                # Upload to backend
                files = {
                    "file": (file_info["filename"], file_bytes, file_info["mime_type"])
                }
                
                upload_resp = await client.post(
                    f"{API_BASE_URL}/files/upload/{work_id}",
                    files=files,
                    timeout=60.0
                )
                
                if upload_resp.status_code not in [200, 201]:
                    logger.error(f"Failed to upload file: {upload_resp.text}")
                    await query.message.reply_text(
                        "⚠️ Работа сохранена, но файл не загружен.\n"
                        "Обратитесь к руководителю.",
                        reply_markup=MAIN_MENU
                    )
                    return ConversationHandler.END
            
            # Success!
            await query.edit_message_text(
                f"✅ Работа успешно отправлена!\n\n"
                f"📝 Название: {title}\n"
                f"📋 ID работы: {work_id}\n\n"
                f"📊 Статус: submitted (на проверке)\n\n"
                f"Вы можете отслеживать статус в разделе «📋 Мои работы»"
            )
            
            await query.message.reply_text(
                "Главное меню:",
                reply_markup=MAIN_MENU
            )
            
    except Exception as e:
        logger.error(f"Error submitting work: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=MAIN_MENU
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel work submission"""
    await update.message.reply_text(
        "❌ Отменено",
        reply_markup=MAIN_MENU
    )
    context.user_data.clear()
    return ConversationHandler.END


# ==================== MAIN HANDLERS ====================

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu buttons"""
    text = update.message.text
    
    if text == "📋 Мои работы":
        await list_my_works(update, context)
    elif text == "💬 Написать руководителю":
        await update.message.reply_text(
            "✍️ Свяжитесь с руководителем:\n"
            "@voodoo_cap",
            reply_markup=MAIN_MENU
        )
    elif text == "📊 Статус":
        await list_my_works(update, context)
    elif text == "❓ Помощь":
        await update.message.reply_text(
            "📚 Помощь:\n\n"
            "• 📋 Мои работы — список и статус работ\n"
            "• ➕ Сдать работу — загрузить новую работу\n"
            "• 💬 Написать руководителю — связь\n\n"
            "Для начала нажмите /start",
            reply_markup=MAIN_MENU
        )


# ==================== MAIN ====================

def main():
    logger.info("DigitalTutor bot v2.3 starting...")
    
    # Create application
    application = Application.builder().token("8662524865:AAHlENmig4dBo5yIdONDq03_pPq9E-j_7y0").build()
    
    # Conversation handler for work submission
    submit_conv = ConversationHandler(
        per_message=False,
        entry_points=[MessageHandler(filters.Regex("➕ Сдать работу"), submit_work_start)],
        states={
            WORK_TYPE: [CallbackQueryHandler(work_type_selected, pattern="^[1-7]$|^cancel$")],
            WORK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, work_title_received)],
            WORK_FILE: [
                MessageHandler(filters.Document.ALL, work_file_received),
                CommandHandler("skip", skip_file)
            ],
            WORK_CONFIRM: [CallbackQueryHandler(confirm_submission, pattern="^confirm$|^cancel$")]
        },
        fallbacks=[CommandHandler("cancel", cancel_submission)]
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(submit_conv)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    
    # Start bot
    application.run_polling()


if __name__ == "__main__":
    main()
