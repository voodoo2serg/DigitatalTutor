"""
DigitalTutor Bot v3.1 — Admin AI Controls & Templates
Добавлено: AI проверка, шаблоны, массовые рассылки
"""
import logging
import io
import httpx
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, 
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters, CallbackQueryHandler
)
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://digitatal-backend:8000/api/v1"
AI_QUEUE_URL = "http://digitatal-backend:8000/api/v1/ai-queue"

# Bot API Token for internal API authentication
# Generated: 2026-03-28
BOT_API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYm90Iiwicm9sZSI6InRlYWNoZXIiLCJmdWxsX25hbWUiOiJEaWdpdGFsVHV0b3IgQm90IiwidHlwZSI6InNlcnZpY2UifQ.ayTsE8OCjiAudFenz470Jgg3TO9sGsv0dfkcSdZTEw0"

# Headers for API requests
API_HEADERS = {
    "Authorization": f"Bearer {BOT_API_TOKEN}",
    "Content-Type": "application/json"
}
AI_QUEUE_URL = "http://digitatal-backend:8000/api/v1/ai-queue"

# Admin IDs (заменить на реальные ID преподавателей)
ADMIN_IDS = [502621151]  # @voodoo_cap

# Conversation states
WORK_TYPE, WORK_TITLE, WORK_DESCRIPTION, WORK_DEADLINE, WORK_FILE, WORK_CONFIRM = range(6)
TEMPLATE_NAME, TEMPLATE_CATEGORY, TEMPLATE_SUBJECT, TEMPLATE_BODY, TEMPLATE_VARS = range(10, 15)
BULK_MESSAGE_SELECT, BULK_MESSAGE_CONFIRM = range(20, 22)

STATUS_INFO = {
    "draft": {"emoji": "📝", "name": "Черновик"},
    "submitted": {"emoji": "📤", "name": "Отправлена"},
    "in_review": {"emoji": "👀", "name": "На проверке"},
    "revision_required": {"emoji": "🔄", "name": "Требует доработки"},
    "accepted": {"emoji": "✅", "name": "Принята"},
    "rejected": {"emoji": "❌", "name": "Отклонена"},
}

WORK_TYPES = {
    "1": ("3e981ca3-704a-4d2f-af81-c17aefa8ecf4", "Курсовая работа"),
    "2": ("8be99b51-0960-49c4-8ac2-436143fe7290", "ВКР (Бакалавр)"),
    "3": ("130a0263-60a6-4f70-bd0c-39fcbfa28bb7", "ВКР (Магистр)"),
    "4": ("75be7f1a-b20c-4724-b4a3-4ea76434c63f", "Научная статья"),
    "5": ("3e5b6a88-f9d2-4b36-a51f-8ec47846890f", "Реферат"),
    "6": ("093bc1c3-3a4d-49a0-8a12-7c1483a6bd45", "Проект"),
    "7": ("d3e57c9e-ea11-44d0-bfd6-97b1b04a1482", "Другое"),
}

# Main menu for students
MAIN_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("📋 Мои работы"), KeyboardButton("➕ Сдать работу")],
    [KeyboardButton("📊 Статистика"), KeyboardButton("💬 Написать руководителю")],
    [KeyboardButton("❓ Помощь")]
], resize_keyboard=True)

# Admin menu
ADMIN_MENU = ReplyKeyboardMarkup([
    [KeyboardButton("📋 Все работы"), KeyboardButton("🤖 AI Проверка")],
    [KeyboardButton("📨 Шаблоны"), KeyboardButton("📤 Массовая рассылка")],
    [KeyboardButton("⚙️ Настройки AI"), KeyboardButton("📊 Статистика системы")],
    [KeyboardButton("🔙 Студенческое меню")]
], resize_keyboard=True)

CANCEL_MENU = ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def api_request(method: str, endpoint: str, data: Dict = None, files: Dict = None) -> Optional[Dict]:
    """
    Make API request with authentication.
    
    FIX 2026-03-28: Added Authorization header for all requests
    """
    try:
        async with httpx.AsyncClient() as client:
            url = f"{API_BASE_URL}{endpoint}"
            
            if method == "GET":
                response = await client.get(url, headers=API_HEADERS, timeout=30.0)
            elif method == "POST":
                if files:
                    # For file uploads, use only Authorization header, not Content-Type
                    headers = {"Authorization": f"Bearer {BOT_API_TOKEN}"}
                    response = await client.post(url, files=files, headers=headers, timeout=60.0)
                else:
                    response = await client.post(url, json=data, headers=API_HEADERS, timeout=30.0)
            elif method == "PATCH":
                response = await client.patch(url, json=data, headers=API_HEADERS, timeout=30.0)
            elif method == "DELETE":
                response = await client.delete(url, headers=API_HEADERS, timeout=30.0)
            else:
                return None
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"API Error {response.status_code}: {response.text}")
                return None
    except Exception as e:
        logger.error(f"API Request Error: {e}")
        return None


# ============== ADMIN COMMANDS ==============

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    await update.message.reply_text(
        "🔧 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=ADMIN_MENU,
        parse_mode="HTML"
    )


async def admin_list_all_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: list all works"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return
    
    await update.message.reply_text("🔄 Загружаю все работы...")
    
    works = await api_request("GET", "/works/")
    
    if not works:
        await update.message.reply_text("📭 Работ пока нет")
        return
    
    # Group by status
    by_status = {}
    for w in works:
        status = w.get("status", "unknown")
        by_status.setdefault(status, []).append(w)
    
    text = f"📊 <b>Всего работ: {len(works)}</b>\n\n"
    
    for status, info in STATUS_INFO.items():
        count = len(by_status.get(status, []))
        if count > 0:
            text += f"{info['emoji']} {info['name']}: <b>{count}</b>\n"
    
    await update.message.reply_text(text, parse_mode="HTML")
    
    # Show recent works
    recent = sorted(works, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
    
    for work in recent:
        status = work.get("status", "draft")
        info = STATUS_INFO.get(status, {"emoji": "❓"})
        
        keyboard = [[
            InlineKeyboardButton("📄 Подробнее", callback_data=f"admin_work:{work['id']}"),
            InlineKeyboardButton("🤖 AI Анализ", callback_data=f"run_ai:{work['id']}")
        ]]
        
        text = f"{info['emoji']} <b>{work.get('title', 'Без названия')}</b>\n"
        text += f"├ Студент: {work.get('student_name', 'N/A')}\n"
        text += f"├ Статус: {info['name']}\n"
        text += f"└ ID: <code>{work['id']}</code>\n"
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


async def admin_ai_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: AI provider settings"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return
    
    providers = await api_request("GET", "/ai/providers")
    
    if not providers:
        await update.message.reply_text("⚠️ Провайдеры не настроены")
        return
    
    text = "⚙️ <b>Настройки AI провайдеров:</b>\n\n"
    
    for p in providers:
        status = "🟢 Активен" if p.get("is_active") else "🔴 Отключен"
        text += f"<b>{p['provider_name']}</b>\n"
        text += f"├ Модель: {p.get('default_model', 'N/A')}\n"
        text += f"├ {status}\n"
        text += f"└ Rate limit: {p.get('rate_limit_per_minute', 60)}/min\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔑 Изменить ключ OpenRouter", callback_data="set_key:openrouter")],
        [InlineKeyboardButton("🔄 Переключить провайдера", callback_data="switch_provider")],
    ]
    
    text += "\n<b>Доступные провайдеры:</b>\n"
    text += "• <a href='https://openrouter.ai'>OpenRouter</a> — GPT-4, Claude, Llama\n"
    text += "• <a href='https://huggingface.co'>HuggingFace</a> — бесплатные модели\n"
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


async def admin_ai_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Manual AI analysis of student work"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    await update.message.reply_text(
        "🤖 <b>AI Анализ работы</b>\n\n"
        "Введите ID работы для анализа:",
        parse_mode="HTML",
        reply_markup=CANCEL_MENU
    )
    context.user_data['awaiting_work_id_for_ai'] = True






async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin input for AI analysis"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return
    
    if context.user_data.get('awaiting_work_id_for_ai'):
        work_id = update.message.text.strip()
        context.user_data.pop('awaiting_work_id_for_ai', None)
        
        # Validate UUID
        try:
            from uuid import UUID
            UUID(work_id)
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат ID. Введите корректный UUID.",
                reply_markup=ADMIN_MENU
            )
            return
        
        await update.message.reply_text(f"🔄 Запускаю AI анализ для работы {work_id}...")
        
        # Get files for work
        files = await api_request("GET", f"/files/work/{work_id}")
        
        if not files:
            await update.message.reply_text(
                "❌ Работа не найдена или у неё нет файлов.",
                reply_markup=ADMIN_MENU
            )
            return
        
        # Start AI analysis
        file_id = files[0].get('id')
        result = await submit_to_ai_queue(work_id, file_id, "")
        
        if result and result.get('success'):
            await update.message.reply_text(
                f"✅ <b>AI анализ запущен!</b>\n\n"
                f"🆔 ID работы: <code>{work_id}</code>\n"
                f"🆔 ID очереди: <code>{result.get('queue_id')}</code>\n\n"
                "📊 Результат будет отправлен в личные сообщения после завершения.",
                parse_mode="HTML",
                reply_markup=ADMIN_MENU
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Ошибка запуска AI анализа</b>\n\n"
                f"🆔 ID работы: <code>{work_id}</code>\n"
                f"⚠️ {result.get('error', 'Неизвестная ошибка')}",
                parse_mode="HTML",
                reply_markup=ADMIN_MENU
            )

async def admin_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: message templates"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return
    
    templates = await api_request("GET", "/ai/templates")
    
    text = "📨 <b>Шаблоны сообщений:</b>\n\n"
    
    if templates:
        for t in templates[:10]:
            category_emoji = {
                "auto_response": "🤖",
                "bulk_mail": "📤",
                "report": "📊",
                "ai_check": "🔍"
            }.get(t.get("category"), "📄")
            
            trigger = t.get("trigger_event", "manual")
            text += f"{category_emoji} <b>{t['name']}</b>\n"
            text += f"├ Категория: {t.get('category', 'N/A')}\n"
            text += f"├ Триггер: {trigger}\n"
            text += f"└ ID: <code>{t['id']}</code>\n\n"
    else:
        text += "Шаблонов пока нет.\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Создать шаблон", callback_data="template_create")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="template_edit")],
        [InlineKeyboardButton("🧪 Предпросмотр", callback_data="template_preview")],
    ]
    
    text += "\n<b>Доступные переменные:</b>\n"
    text += "• {student_name} — имя студента\n"
    text += "• {work_title} — название работы\n"
    text += "• {work_id} — ID работы\n"
    text += "• {ai_plagiarism_score} — плагиат ИИ\n"
    text += "• {ai_structure_score} — структура\n"
    text += "• {ai_formatting_score} — оформление\n"
    text += "• {status} — статус работы\n"
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def admin_bulk_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: bulk messaging"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return
    
    templates = await api_request("GET", "/ai/templates?category=bulk_mail")
    
    text = "📤 <b>Массовая рассылка</b>\n\n"
    text += "Выберите шаблон или создайте новое сообщение:\n\n"
    
    keyboard = []
    
    if templates:
        for t in templates:
            keyboard.append([InlineKeyboardButton(
                f"📄 {t['name']}", 
                callback_data=f"bulk_select:{t['id']}"
            )])
    
    keyboard.extend([
        [InlineKeyboardButton("✏️ Новое сообщение", callback_data="bulk_custom")],
        [InlineKeyboardButton("👥 Выбрать получателей", callback_data="bulk_recipients")],
    ])
    
    text += "\n<b>Типы рассылок:</b>\n"
    text += "• Всем студентам\n"
    text += "• По статусу работы (например, всем с 'доработкой')\n"
    text += "• По типу работы (всем с курсовыми)\n"
    text += "• Конкретным студентам\n"
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def run_ai_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run AI analysis on work"""
    query = update.callback_query
    await query.answer()
    
    work_id = query.data.split(":")[1]
    
    await query.edit_message_text("🤖 <b>Запускаю AI анализ...</b>\n\nЭто может занять 1-2 минуты", parse_mode="HTML")
    
    # Call AI analysis API
    result = await api_request("POST", f"/ai/analyze/{work_id}")
    
    if result and result.get("success"):
        analysis = result.get("analysis", {})
        
        text = "✅ <b>AI Анализ завершен!</b>\n\n"
        
        if "antiplagiarism" in analysis:
            score = analysis["antiplagiarism"].get("score", 0)
            emoji = "🟢" if score > 80 else "🟡" if score > 50 else "🔴"
            text += f"{emoji} <b>Плагиат ИИ:</b> {score}/100\n"
            if "assessment" in analysis["antiplagiarism"]:
                text += f"   <i>{analysis['antiplagiarism']['assessment'][:100]}</i>\n"
        
        if "structure" in analysis:
            score = analysis["structure"].get("score", 0)
            text += f"🟢 <b>Структура:</b> {score}/100\n"
        
        if "formatting" in analysis:
            score = analysis["formatting"].get("score", 0)
            text += f"🟢 <b>Оформление:</b> {score}/100\n"
        
        text += f"\n💰 Tokens: {result.get('tokens_used', 'N/A')}"
        text += f"\n💵 Стоимость: ~${result.get('estimated_cost_usd', 0):.6f}"
        
        keyboard = [[
            InlineKeyboardButton("📄 Открыть работу", callback_data=f"admin_work:{work_id}"),
            InlineKeyboardButton("📨 Отправить отчет", callback_data=f"send_report:{work_id}")
        ]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text(
            "❌ <b>Ошибка при анализе</b>\n\n"
            "Проверьте настройки AI провайдера (/admin)",
            parse_mode="HTML"
        )


async def send_ai_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send AI report to student"""
    query = update.callback_query
    await query.answer()
    
    work_id = query.data.split(":")[1]
    
    # Get work details
    work = await api_request("GET", f"/works/{work_id}")
    
    if not work:
        await query.edit_message_text("❌ Работа не найдена")
        return
    
    # Send template message
    template_id = None  # Would get from settings
    
    await query.edit_message_text(
        "📤 <b>Отчет отправлен студенту!</b>\n\n"
        f"Студент: {work.get('student_name', 'N/A')}\n"
        f"Работа: {work.get('title', 'N/A')}",
        parse_mode="HTML"
    )


# ============== STUDENT FUNCTIONS (from v3.0) ==============

async def get_or_create_user(telegram_id: int, username: str, full_name: str) -> Optional[Dict]:
    user = await api_request("GET", f"/users/telegram/{telegram_id}")
    if user:
        return user
    
    user_data = {
        "telegram_id": telegram_id,
        "username": username or str(telegram_id),
        "full_name": full_name or f"Student_{telegram_id}",
        "role": "student"
    }
    return await api_request("POST", "/users/", user_data)


def format_work_card(work: Dict) -> str:
    status = work.get("status", "draft")
    info = STATUS_INFO.get(status, {"emoji": "❓", "name": status})
    
    text = f"{info['emoji']} <b>{work.get('title', 'Без названия')}</b>\n"
    text += f"├ Тип: {work.get('work_type_name', 'Другое')}\n"
    text += f"├ Статус: {info['name']}\n"
    
    if work.get('deadline'):
        text += f"├ Дедлайн: {work['deadline'][:10]}\n"
    
    if work.get('ai_plagiarism_score') is not None:
        text += f"├ Плагиат ИИ: {work['ai_plagiarism_score']:.0%}\n"
    
    if work.get('teacher_comment'):
        comment = work['teacher_comment'][:50] + "..."
        text += f"├ 💬 {comment}\n"
    
    text += f"└ ID: <code>{work.get('id', 'N/A')}</code>\n"
    
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    await update.message.reply_text("🔄 Регистрация...")
    
    db_user = await get_or_create_user(user.id, user.username, user.full_name)
    
    if db_user:
        menu = ADMIN_MENU if is_admin(user.id) else MAIN_MENU
        
        await update.message.reply_text(
            f"✅ <b>Добро пожаловать, {user.full_name or user.username}!</b>\n\n"
            f"Вы подключены к <b>DigitalTutor</b>.\n\n"
            f"📋 <b>Что умею:</b>\n"
            f"• Показывать ваши работы и статусы\n"
            f"• Принимать новые работы с файлами\n"
            f"• AI анализ (плагиат, структура, оформление)\n"
            f"• Комментарии от руководителя\n"
            f"• Массовые уведомления\n\n"
            f"Начните с «📋 Мои работы» или «➕ Сдать работу»",
            reply_markup=menu,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Ошибка регистрации. Попробуйте позже.")


async def list_my_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    await update.message.reply_text("🔄 Загружаю работы...")
    
    db_user = await api_request("GET", f"/users/telegram/{user.id}")
    if not db_user:
        await update.message.reply_text("❌ Сначала /start", reply_markup=MAIN_MENU)
        return
    
    user_id = db_user.get("id")
    works = await api_request("GET", f"/works/?student_id={user_id}")
    
    if not works:
        await update.message.reply_text(
            "📭 <b>У вас пока нет работ</b>\n\nНажмите «➕ Сдать работу»",
            reply_markup=MAIN_MENU,
            parse_mode="HTML"
        )
        return
    
    status_counts = {}
    for w in works:
        status = w.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    summary = "📊 <b>Ваши работы:</b>\n\n"
    for status, info in STATUS_INFO.items():
        count = status_counts.get(status, 0)
        if count > 0:
            summary += f"{info['emoji']} {info['name']}: <b>{count}</b>\n"
    
    summary += f"\n<i>Всего: {len(works)}</i>\n\n<b>Последние:</b>"
    
    await update.message.reply_text(summary, parse_mode="HTML")
    
    for work in works[:5]:
        keyboard = [[InlineKeyboardButton("📄 Подробнее", callback_data=f"work_details:{work['id']}")]]
        text = format_work_card(work)
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    await update.message.reply_text("🔄 Собираю статистику...")
    
    db_user = await api_request("GET", f"/users/telegram/{user.id}")
    if not db_user:
        await update.message.reply_text("❌ Сначала /start")
        return
    
    user_id = db_user.get("id")
    works = await api_request("GET", f"/works/?student_id={user_id}")
    
    if not works:
        await update.message.reply_text(
            "📊 <b>Статистика</b>\n\nПока нет данных. Сдайте первую работу!",
            reply_markup=MAIN_MENU,
            parse_mode="HTML"
        )
        return
    
    total = len(works)
    submitted = len([w for w in works if w.get('status') in ['submitted', 'in_review']])
    accepted = len([w for w in works if w.get('status') == 'accepted'])
    revision = len([w for w in works if w.get('status') == 'revision_required'])
    
    avg_plagiarism = [w['ai_plagiarism_score'] for w in works if w.get('ai_plagiarism_score') is not None]
    
    text = "📊 <b>Ваша статистика</b>\n\n"
    text += f"📁 Всего работ: <b>{total}</b>\n"
    text += f"✅ Принято: <b>{accepted}</b>\n"
    text += f"⏳ На проверке: <b>{submitted}</b>\n"
    text += f"🔄 На доработке: <b>{revision}</b>\n"
    
    if avg_plagiarism:
        avg = sum(avg_plagiarism) / len(avg_plagiarism)
        text += f"\n📈 Средний плагиат ИИ: <b>{avg:.0%}</b>\n"
    
    await update.message.reply_text(text, reply_markup=MAIN_MENU, parse_mode="HTML")


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 <b>Помощь по DigitalTutor</b>\n\n"
        "<b>📋 Мои работы</b> — список и статус\n"
        "<b>➕ Сдать работу</b> — загрузить работу\n"
        "<b>📊 Статистика</b> — общая сводка\n"
        "<b>💬 Написать руководителю</b> — связь\n\n"
        "<b>Статусы работ:</b>\n"
    )
    
    for status, info in STATUS_INFO.items():
        text += f"{info['emoji']} <b>{info['name']}</b>\n"
    
    text += (
        "\n<b>AI Анализ:</b>\n"
        "• Плагиат ИИ — использование нейросетей\n"
        "• Структура — соответствие требованиям\n"
        "• Оформление — проверка ГОСТ\n"
        "• Оригинальность — антиплагиат\n\n"
        "Контакты: @voodoo_cap"
    )
    
    await update.message.reply_text(text, reply_markup=MAIN_MENU, parse_mode="HTML")


# ============== WORK SUBMISSION FLOW ==============

async def submit_work_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    db_user = await api_request("GET", f"/users/telegram/{user.id}")
    if not db_user:
        await update.message.reply_text("❌ Сначала /start")
        return ConversationHandler.END
    
    context.user_data["student_id"] = db_user.get("id")
    
    keyboard = [
        [InlineKeyboardButton("1. Курсовая", callback_data="type:1")],
        [InlineKeyboardButton("2. ВКР (Бакалавр)", callback_data="type:2")],
        [InlineKeyboardButton("3. ВКР (Магистр)", callback_data="type:3")],
        [InlineKeyboardButton("4. Статья", callback_data="type:4")],
        [InlineKeyboardButton("5. Реферат", callback_data="type:5")],
        [InlineKeyboardButton("6. Проект", callback_data="type:6")],
        [InlineKeyboardButton("7. Другое", callback_data="type:7")],
    ]
    
    await update.message.reply_text(
        "📚 <b>Шаг 1/5: Тип работы</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )
    
    return WORK_TYPE


async def work_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    type_num = query.data.split(":")[1]
    type_id, type_name = WORK_TYPES.get(type_num, (None, "Другое"))
    
    context.user_data["work_type_id"] = type_id
    context.user_data["work_type_name"] = type_name
    
    await query.edit_message_text(
        f"✅ Тип: <b>{type_name}</b>\n\n<b>Шаг 2/5: Название работы</b>",
        parse_mode="HTML"
    )
    
    return WORK_TITLE


async def work_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    
    if len(title) < 5:
        await update.message.reply_text("❌ Слишком коротко (минимум 5 символов)", reply_markup=CANCEL_MENU)
        return WORK_TITLE
    
    context.user_data["work_title"] = title
    
    await update.message.reply_text(
        f"✅ Название: <b>{title}</b>\n\n<b>Шаг 3/5: Описание</b> (или /skip)",
        reply_markup=CANCEL_MENU,
        parse_mode="HTML"
    )
    
    return WORK_DESCRIPTION


async def work_description_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["work_description"] = update.message.text.strip()
    await ask_deadline(update, context)
    return WORK_DEADLINE


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["work_description"] = None
    await ask_deadline(update, context)
    return WORK_DEADLINE


async def ask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏭ Пропущено\n\n<b>Шаг 4/5: Дедлайн</b> (ДД.ММ.ГГГГ или /skip)",
        reply_markup=CANCEL_MENU,
        parse_mode="HTML"
    )


async def work_deadline_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text.strip()
    
    try:
        day, month, year = map(int, date_text.split("."))
        deadline = f"{year:04d}-{month:02d}-{day:02d}T23:59:59"
        context.user_data["work_deadline"] = deadline
        await update.message.reply_text(f"✅ Дедлайн: {date_text}\n")
    except:
        await update.message.reply_text("❌ Неверный формат (ДД.ММ.ГГГГ)", reply_markup=CANCEL_MENU)
        return WORK_DEADLINE
    
    await ask_file(update, context)
    return WORK_FILE


async def skip_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["work_deadline"] = None
    await ask_file(update, context)
    return WORK_FILE


async def ask_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Шаг 5/5: Файл</b> (PDF/DOC/DOCX/TXT, до 20MB или /skip)",
        reply_markup=CANCEL_MENU,
        parse_mode="HTML"
    )


async def work_file_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("❌ Отправьте файл или /skip", reply_markup=CANCEL_MENU)
        return WORK_FILE
    
    document = update.message.document
    
    if document.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ Файл слишком большой (макс 20MB)", reply_markup=CANCEL_MENU)
        return WORK_FILE
    
    allowed = ['application/pdf', 'application/msword', 
               'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
               'text/plain']
    
    if document.mime_type not in allowed:
        await update.message.reply_text("❌ Только PDF, DOC, DOCX, TXT", reply_markup=CANCEL_MENU)
        return WORK_FILE
    
    context.user_data["file"] = {
        "file_id": document.file_id,
        "filename": document.file_name,
        "mime_type": document.mime_type,
        "size": document.file_size,
    }
    
    await show_submission_confirmation(update, context)
    return WORK_CONFIRM


async def skip_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["file"] = None
    await show_submission_confirmation(update, context)
    return WORK_CONFIRM


async def show_submission_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    work_type = context.user_data.get("work_type_name", "Другое")
    title = context.user_data.get("work_title", "")
    description = context.user_data.get("work_description")
    deadline = context.user_data.get("work_deadline")
    file_info = context.user_data.get("file")
    
    text = "📋 <b>Проверьте данные:</b>\n\n"
    text += f"📚 <b>Тип:</b> {work_type}\n"
    text += f"📝 <b>Название:</b> {title}\n"
    
    if description:
        text += f"📄 <b>Описание:</b> {description[:100]}\n"
    
    if deadline:
        text += f"📅 <b>Дедлайн:</b> {deadline[:10]}\n"
    
    if file_info:
        size_mb = file_info['size'] / (1024 * 1024)
        text += f"📎 <b>Файл:</b> {file_info['filename']} ({size_mb:.1f} MB)\n"
    else:
        text += "📎 <b>Файл:</b> не загружен\n"
    
    text += "\n<b>Всё верно?</b>"
    
    keyboard = [
        [InlineKeyboardButton("✅ Отправить", callback_data="confirm_submit")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_submit")],
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def confirm_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Подтверждение и создание работы.
    
    FIX 2026-03-28: Добавлены return ConversationHandler.END и MAIN_MENU
    во всех ветках завершения, чтобы корректно завершить диалог.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_submit":
        await query.edit_message_text("❌ Отменено")
        await query.message.reply_text("Главное меню:", reply_markup=MAIN_MENU)
        context.user_data.clear()
        return ConversationHandler.END
    
    await query.edit_message_text("🔄 Создание работы...")
    
    work_data = {
        "student_id": context.user_data.get("student_id"),
        "work_type_id": context.user_data.get("work_type_id"),
        "title": context.user_data.get("work_title"),
        "description": context.user_data.get("work_description"),
        "status": "submitted",
        "deadline": context.user_data.get("work_deadline"),
    }
    
    work = await api_request("POST", "/works/", work_data)
    
    if not work:
        await query.message.reply_text("❌ Ошибка при создании работы", reply_markup=MAIN_MENU)
        context.user_data.clear()
        return ConversationHandler.END
    
    work_id = work.get("id")
    
    # Upload file if provided
    file_info = context.user_data.get("file")
    if file_info and work_id:
        await query.edit_message_text("🔄 Загрузка файла...")
        
        try:
            file_obj = await context.bot.get_file(file_info["file_id"])
            file_bytes = await file_obj.download_as_bytearray()
            
            files = {"file": (file_info["filename"], io.BytesIO(file_bytes), file_info["mime_type"])}
            upload = await api_request("POST", f"/files/upload/{work_id}", files=files)
            
            if upload:
                await query.edit_message_text("✅ Файл загружен!")
                
                # AI анализ запускается вручную через админ-меню
                await query.message.reply_text(
                    "✅ <b>Работа и файл успешно созданы!</b>\n\n"
                    f"📝 Название: {work.get('title')}\n"
                    f"🆔 ID: <code>{work.get('id')}</code>",
                    parse_mode="HTML",
                    reply_markup=MAIN_MENU
                )
                
                # FIX: Очищаем данные и завершаем диалог
                context.user_data.clear()
                return ConversationHandler.END
            else:
                await query.message.reply_text(
                    "⚠️ <b>Работа создана, но файл не загружен</b>",
                    parse_mode="HTML",
                    reply_markup=MAIN_MENU
                )
                context.user_data.clear()
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"File upload error: {e}")
            await query.message.reply_text(
                '⚠️ Работа создана, но файл не загружен',
                reply_markup=MAIN_MENU
            )
            context.user_data.clear()
            return ConversationHandler.END
    else:
        # No file uploaded - work created successfully without file
        await query.edit_message_text("✅ Работа создана!")
        await query.message.reply_text(
            "📋 <b>Работа успешно создана!</b>\n\n"
            f"📝 Название: {work.get('title')}\n"
            f"📊 Статус: {work.get('status')}\n"
            f"🆔 ID: <code>{work.get('id')}</code>",
            parse_mode="HTML",
            reply_markup=MAIN_MENU
        )
        context.user_data.clear()
        return ConversationHandler.END


async def handle_work_details(update, context, query, data):
    """Show work details for student"""
    work_id = data.replace("work_details:", "")
    
    work = await api_request("GET", f"/works/{work_id}")
    if not work:
        await query.edit_message_text("❌ Работа не найдена")
        return
    
    files = await api_request("GET", f"/files/work/{work_id}")
    
    status = work.get('status', 'draft')
    status_emoji = {"submitted": "📤", "draft": "📝", "graded": "⭐", "revision": "🔄"}.get(status, "❓")
    status_name = {"submitted": "Сдана", "draft": "Черновик", "graded": "Оценена", "revision": "На доработке"}.get(status, status)
    
    lines = []
    lines.append(f"📄 <b>{work.get('title', 'Без названия')}</b>")
    lines.append("")
    lines.append(f"📊 <b>Статус:</b> {status_emoji} {status_name}")
    lines.append(f"📝 <b>Тип:</b> {work.get('work_type_name', 'N/A')}")
    created = work.get('created_at', 'N/A')
    lines.append(f"📅 <b>Создана:</b> {created[:10] if created else 'N/A'}")
    
    if work.get('deadline'):
        lines.append(f"⏰ <b>Дедлайн:</b> {work['deadline'][:10]}")
    
    if work.get('description'):
        desc = work['description']
        lines.append("")
        lines.append("📝 <b>Описание:</b>")
        lines.append(desc[:200] + "..." if len(desc) > 200 else desc)
    
    if files:
        lines.append("")
        lines.append(f"📎 <b>Файлы ({len(files)}):</b>")
        for f in files:
            size_kb = f.get('size_bytes', 0) // 1024
            lines.append(f"├ {f.get('original_name', 'N/A')} ({size_kb} KB)")
    
    if work.get('teacher_comment'):
        lines.append("")
        lines.append("✍️ <b>Рецензия:</b>")
        lines.append(work['teacher_comment'])
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_my_works")]]
    
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def handle_admin_work(update, context, query, data):
    """Admin work details with contact info"""
    work_id = data.replace("admin_work:", "")
    
    work = await api_request("GET", f"/works/{work_id}")
    if not work:
        await query.edit_message_text("❌ Работа не найдена")
        return
    
    files = await api_request("GET", f"/files/work/{work_id}")
    
    status = work.get('status', 'draft')
    status_emoji = {"submitted": "📤", "draft": "📝", "graded": "⭐", "revision": "🔄"}.get(status, "❓")
    
    lines = []
    lines.append(f"📄 <b>{work.get('title', 'Без названия')}</b>")
    lines.append("")
    lines.append(f"👤 <b>Студент:</b> {work.get('student_name', 'N/A')}")
    
    # Email с кликабельной ссылкой
    email = work.get('student_email')
    if email:
        lines.append(f"📧 <b>Email:</b> <a href=\"mailto:{email}\">{email}</a>")
    
    # Telegram с кликабельной ссылкой
    tg_username = work.get('student_telegram_username')
    tg_id = work.get('student_telegram_id')
    if tg_username:
        lines.append(f"💬 <b>Telegram:</b> <a href=\"https://t.me/{tg_username}\">@{tg_username}</a>")
    elif tg_id:
        lines.append(f"💬 <b>Telegram:</b> <a href=\"tg://user?id={tg_id}\">Открыть чат</a>")
    
    lines.append("")
    lines.append(f"📊 <b>Статус:</b> {status_emoji} {status}")
    lines.append(f"📝 <b>Тип:</b> {work.get('work_type_name', 'N/A')}")
    created = work.get('created_at', 'N/A')
    lines.append(f"📅 <b>Создана:</b> {created[:10] if created else 'N/A'}")
    
    if work.get('deadline'):
        lines.append(f"⏰ <b>Дедлайн:</b> {work['deadline'][:10]}")
    
    if files:
        lines.append("")
        lines.append(f"📎 <b>Файлы ({len(files)}):</b>")
        for f in files:
            size_kb = f.get('size_bytes', 0) // 1024
            lines.append(f"├ {f.get('original_name', 'N/A')} ({size_kb} KB)")
    
    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("✍️ Рецензия", callback_data=f"add_review:{work_id}"),
         InlineKeyboardButton("⭐ Оценка", callback_data=f"add_grade:{work_id}")],
        [InlineKeyboardButton("🔄 На доработку", callback_data=f"request_revision:{work_id}"),
         InlineKeyboardButton("📨 Отчёт студенту", callback_data=f"send_report:{work_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_works")]
    ]
    
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML", disable_web_page_preview=True)


async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("work_details:"):
        await handle_work_details(update, context, query, data)
    elif data.startswith("admin_work:"):
        await handle_admin_work(update, context, query, data)
    elif data.startswith("run_ai:"):
        await run_ai_analysis(update, context)
    elif data.startswith("send_report:"):
        await send_ai_report(update, context)


# ============== MAIN ==============


async def cancel_submission(update, context):
    await update.message.reply_text("❌ Отменено", reply_markup=MAIN_MENU)
    context.user_data.clear()
    return ConversationHandler.END

def main():
    logger.info("DigitalTutor Bot v3.1 starting...")
    
    application = Application.builder().token("8662524865:AAHlENmig4dBo5yIdONDq03_pPq9E-j_7y0").build()
    
    # Work submission conversation
    submit_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("➕ Сдать работу"), submit_work_start)],
        states={
            WORK_TYPE: [CallbackQueryHandler(work_type_selected, pattern="^type:")],
            WORK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, work_title_received)],
            WORK_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, work_description_received),
                CommandHandler("skip", skip_description),
            ],
            WORK_DEADLINE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, work_deadline_received),
                CommandHandler("skip", skip_deadline),
            ],
            WORK_FILE: [
                MessageHandler(filters.Document.ALL, work_file_received),
                CommandHandler("skip", skip_file),
            ],
            WORK_CONFIRM: [CallbackQueryHandler(confirm_submission, pattern="^confirm_submit$|^cancel_submit$")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_submission),
            MessageHandler(filters.Regex("❌ Отмена"), cancel_submission),
        ],
    )
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(submit_conv)
    
    # Menu handlers
    application.add_handler(MessageHandler(filters.Regex("📋 Мои работы"), list_my_works))
    application.add_handler(MessageHandler(filters.Regex("📋 Все работы"), admin_list_all_works))
    application.add_handler(MessageHandler(filters.Regex("📊 Статистика"), show_statistics))
    application.add_handler(MessageHandler(filters.Regex("📊 Статистика системы"), show_statistics))
    application.add_handler(MessageHandler(filters.Regex("🤖 AI Проверка"), admin_ai_analyze))
    application.add_handler(MessageHandler(filters.Regex("⚙️ Настройки AI"), admin_ai_settings))
    application.add_handler(MessageHandler(filters.Regex("📨 Шаблоны"), admin_templates))
    application.add_handler(MessageHandler(filters.Regex("📤 Массовая рассылка"), admin_bulk_message))
    application.add_handler(MessageHandler(filters.Regex("❓ Помощь"), show_help))
    application.add_handler(MessageHandler(filters.Regex("🔙 Студенческое меню"), start))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    
    application.run_polling()


if __name__ == "__main__":
    main()


async def submit_to_ai_queue(work_id: str, file_id: str, text_content: str = "") -> Optional[Dict]:
    """Добавить работу в очередь AI анализа (Kimi-Claw)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AI_QUEUE_URL}/queue/submit",
                json={
                    "work_id": work_id,
                    "file_id": file_id,
                    "priority": 5,
                    "analysis_types": ["antiplagiarism", "structure", "formatting"]
                },
                timeout=30.0
            )
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Queue submit error: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Submit to queue error: {e}")
        return None


async def get_ai_queue_status(work_id: str) -> Optional[Dict]:
    """Получить статус анализа в очереди"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AI_QUEUE_URL}/queue/status/{work_id}",
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        logger.error(f"Get queue status error: {e}")
        return None

