#!/usr/bin/env python3
"""
DigitalTutor - Мастер управления ботом

Панель управления для преподавателя:
- Редактирование текстов бота
- Создание цепочек заданий (milestone chains)
- Управление кодами доступа
- Массовые рассылки
- Статистика и отчёты
"""

import os
import sys
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

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
TEACHER_TELEGRAM_ID = int(os.getenv("TEACHER_TELEGRAM_ID", "0"))
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "/srv/teaching-system/config"))

# Сообщения
ADMIN_MESSAGES = {
    "welcome": """🎛️ Панель управления DigitalTutor

Выберите раздел для настройки:""",

    "texts_menu": """📝 Редактирование текстов бота

Выберите текст для редактирования:""",

    "chains_menu": """🔗 Цепочки заданий (Milestone Chains)

Цепочки определяют этапы для разных типов работ.
Выберите действие:""",

    "codes_menu": """🎫 Коды доступа

Коды позволяют создавать специальные сценарии регистрации.
Например, для конференции или быстрой регистрации на рецензирование.""",

    "edit_prompt": """✏️ Редактирование: {field_name}

Текущее значение:
---
{current_value}
---

Введите новое значение или /cancel для отмены:""",

    "saved": """✅ Сохранено!

Изменения вступят в силу немедленно.""",

    "chain_created": """✅ Цепочка создана!

Имя: {name}
Этапов: {steps_count}
Тип работ: {work_types}

Цепочка готова к использованию.""",

    "code_created": """✅ Код доступа создан!

Код: {code}
Срок действия: {expires}
Ограничение использований: {max_uses}

Для использования студент должен отправить:
/start {code}"""
}

# =============================================================================
# МЕНЮ И КЛАВИАТУРЫ
# =============================================================================

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("📝 Тексты бота", callback_data="admin:texts")],
        [InlineKeyboardButton("🔗 Цепочки заданий", callback_data="admin:chains")],
        [InlineKeyboardButton("🎫 Коды доступа", callback_data="admin:codes")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin:settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_texts_keyboard() -> InlineKeyboardMarkup:
    """Меню редактирования текстов"""
    keyboard = [
        [InlineKeyboardButton("👋 Приветствие", callback_data="edit:welcome")],
        [InlineKeyboardButton("❓ Справка", callback_data="edit:help")],
        [InlineKeyboardButton("📅 Напоминания", callback_data="edit:reminders")],
        [InlineKeyboardButton("📊 Сообщения статусов", callback_data="edit:status_msgs")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_chains_keyboard() -> InlineKeyboardMarkup:
    """Меню цепочек заданий"""
    keyboard = [
        [InlineKeyboardButton("📋 Список цепочек", callback_data="chains:list")],
        [InlineKeyboardButton("➕ Создать цепочку", callback_data="chains:create")],
        [InlineKeyboardButton("✏️ Редактировать", callback_data="chains:edit")],
        [InlineKeyboardButton("🗑️ Удалить", callback_data="chains:delete")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_codes_keyboard() -> InlineKeyboardMarkup:
    """Меню кодов доступа"""
    keyboard = [
        [InlineKeyboardButton("📋 Активные коды", callback_data="codes:list")],
        [InlineKeyboardButton("➕ Создать код", callback_data="codes:create")],
        [InlineKeyboardButton("🗑️ Отозвать код", callback_data="codes:revoke")],
        [InlineKeyboardButton("◀️ Назад", callback_data="admin:main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# =============================================================================
# СОСТОЯНИЯ
# =============================================================================

admin_states: Dict[int, Dict[str, Any]] = {}

class AdminState:
    MAIN = "main"
    EDIT_TEXT = "edit_text"
    CREATE_CHAIN = "create_chain"
    CREATE_CODE = "create_code"
    BROADCAST = "broadcast"

# =============================================================================
# ОБРАБОТЧИКИ КОМАНД
# =============================================================================

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в панель управления"""
    user_id = update.effective_user.id
    
    # Проверяем права
    if user_id != TEACHER_TELEGRAM_ID:
        await update.message.reply_text("⛔ У вас нет доступа к панели управления.")
        return
    
    admin_states[user_id] = {"state": AdminState.MAIN}
    
    await update.message.reply_text(
        ADMIN_MESSAGES["welcome"],
        reply_markup=get_main_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id != TEACHER_TELEGRAM_ID:
        return
    
    data = query.data
    
    # Главное меню
    if data == "admin:main":
        admin_states[user_id] = {"state": AdminState.MAIN}
        await query.message.edit_text(
            ADMIN_MESSAGES["welcome"],
            reply_markup=get_main_keyboard()
        )
    
    # Тексты бота
    elif data == "admin:texts":
        await query.message.edit_text(
            ADMIN_MESSAGES["texts_menu"],
            reply_markup=get_texts_keyboard()
        )
    
    # Цепочки заданий
    elif data == "admin:chains":
        await query.message.edit_text(
            ADMIN_MESSAGES["chains_menu"],
            reply_markup=get_chains_keyboard()
        )
    
    # Коды доступа
    elif data == "admin:codes":
        await query.message.edit_text(
            ADMIN_MESSAGES["codes_menu"],
            reply_markup=get_codes_keyboard()
        )
    
    # Редактирование текстов
    elif data.startswith("edit:"):
        field = data.split(":")[1]
        await start_edit_text(query, context, user_id, field)
    
    # Рассылка
    elif data == "admin:broadcast":
        await start_broadcast(query, context, user_id)
    
    # Статистика
    elif data == "admin:stats":
        await show_stats(query, context)
    
    # Цепочки
    elif data == "chains:list":
        await show_chains_list(query, context)
    elif data == "chains:create":
        await start_create_chain(query, context, user_id)
    
    # Коды
    elif data == "codes:list":
        await show_codes_list(query, context)
    elif data == "codes:create":
        await start_create_code(query, context, user_id)

# =============================================================================
# РЕДАКТИРОВАНИЕ ТЕКСТОВ
# =============================================================================

async def start_edit_text(
    query, 
    context: ContextTypes.DEFAULT_TYPE, 
    user_id: int, 
    field: str
):
    """Начало редактирования текста"""
    
    # Загружаем текущее значение
    current_value = await load_text_field(field)
    
    field_names = {
        "welcome": "Приветствие",
        "help": "Справка",
        "reminders": "Напоминания о дедлайнах",
        "status_msgs": "Сообщения об изменении статуса"
    }
    
    admin_states[user_id] = {
        "state": AdminState.EDIT_TEXT,
        "field": field
    }
    
    await query.message.edit_text(
        ADMIN_MESSAGES["edit_prompt"].format(
            field_name=field_names.get(field, field),
            current_value=current_value or "(пусто)"
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="admin:texts")
        ]])
    )

async def load_text_field(field: str) -> str:
    """Загрузка текстового поля из конфига"""
    config_file = CONFIG_DIR / "bot_texts.yaml"
    
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get(field, "")
    
    # Значения по умолчанию
    defaults = {
        "welcome": "👋 Привет! Я ваш помощник для работы с учебными проектами.",
        "help": "📚 Справка по командам...",
        "reminders": "📅 Напоминание о дедлайне...",
        "status_msgs": "📊 Статус вашей работы изменён..."
    }
    return defaults.get(field, "")

async def save_text_field(field: str, value: str) -> bool:
    """Сохранение текстового поля"""
    config_file = CONFIG_DIR / "bot_texts.yaml"
    
    config = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    
    config[field] = value
    
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    return True

# =============================================================================
# ЦЕПОЧКИ ЗАДАНИЙ
# =============================================================================

async def show_chains_list(query, context: ContextTypes.DEFAULT_TYPE):
    """Показать список цепочек"""
    chains = await load_milestone_chains()
    
    if not chains:
        text = "📭 Цепочки не созданы.\n\nСоздайте первую цепочку через меню."
    else:
        text = "📋 Цепочки заданий:\n\n"
        for code, chain in chains.items():
            steps = chain.get("milestones", [])
            text += f"""🔹 {chain.get('name', code)}
   Этапов: {len(steps)}
   Код: {code}

"""
    
    await query.message.edit_text(
        text,
        reply_markup=get_chains_keyboard()
    )

async def start_create_chain(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Начало создания цепочки"""
    admin_states[user_id] = {
        "state": AdminState.CREATE_CHAIN,
        "step": "name",
        "data": {}
    }
    
    await query.message.edit_text(
        """➕ Создание новой цепочки

Шаг 1: Введите название цепочки (например, "Курсовая работа - ускоренный курс"):""",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="admin:chains")
        ]])
    )

async def load_milestone_chains() -> Dict[str, Any]:
    """Загрузка цепочек из конфига"""
    config_file = CONFIG_DIR / "milestone_chains.yaml"
    
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    return {}

# =============================================================================
# КОДЫ ДОСТУПА
# =============================================================================

async def show_codes_list(query, context: ContextTypes.DEFAULT_TYPE):
    """Показать список кодов"""
    codes = await load_access_codes()
    
    if not codes:
        text = "📭 Активных кодов нет.\n\nСоздайте код для специального сценария регистрации."
    else:
        text = "🎫 Активные коды доступа:\n\n"
        for code_data in codes:
            status = "✅" if code_data.get("is_active") else "❌"
            text += f"""{status} {code_data['code']}
   Назначение: {code_data.get('description', '-')}
   Использований: {code_data.get('used_count', 0)}/{code_data.get('max_uses', '∞')}
   
"""
    
    await query.message.edit_text(
        text,
        reply_markup=get_codes_keyboard()
    )

async def start_create_code(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Начало создания кода"""
    admin_states[user_id] = {
        "state": AdminState.CREATE_CODE,
        "step": "code",
        "data": {}
    }
    
    await query.message.edit_text(
        """🎫 Создание кода доступа

Шаг 1: Введите код (только латиница и цифры, например: CONF2024):""",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Отмена", callback_data="admin:codes")
        ]])
    )

async def load_access_codes() -> List[Dict[str, Any]]:
    """Загрузка кодов из БД"""
    # TODO: Реализовать загрузку из БД
    return []

# =============================================================================
# РАССЫЛКА
# =============================================================================

async def start_broadcast(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Начало рассылки"""
    admin_states[user_id] = {
        "state": AdminState.BROADCAST,
        "step": "target"
    }
    
    keyboard = [
        [InlineKeyboardButton("📧 Всем студентам", callback_data="bc:all")],
        [InlineKeyboardButton("📁 По типу работы", callback_data="bc:by_type")],
        [InlineKeyboardButton("📅 По дедлайну", callback_data="bc:by_deadline")],
        [InlineKeyboardButton("◀️ Отмена", callback_data="admin:main")]
    ]
    
    await query.message.edit_text(
        """📢 Массовая рассылка

Выберите получателей:""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =============================================================================
# СТАТИСТИКА
# =============================================================================

async def show_stats(query, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    # TODO: Загрузить реальную статистику из БД
    
    stats_text = """📊 Статистика системы

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 ЗАГРУЗКА:
• На проверке: 12 работ
• Сдано сегодня: 3 работы
• Дедлайны на неделе: 8 работ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👥 СТУДЕНТЫ:
• Всего зарегистрировано: 45
• Активных: 38
• Аспирантов: 7

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 ПО ТИПАМ РАБОТ:
• Курсовые: 23
• ВКР: 8
• Статьи: 12
• Проекты: 5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 AI-АНАЛИЗ:
• Обработано файлов: 34
• Среднее время: 12 сек
• Токенов использовано: 125K
"""
    
    await query.message.edit_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="admin:main")
        ]])
    )

# =============================================================================
# ОБРАБОТКА СООБЩЕНИЙ
# =============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений в режиме администратора"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id != TEACHER_TELEGRAM_ID:
        return
    
    if user_id not in admin_states:
        return
    
    state_data = admin_states[user_id]
    state = state_data.get("state")
    
    if state == AdminState.EDIT_TEXT:
        # Сохраняем отредактированный текст
        field = state_data.get("field")
        await save_text_field(field, text)
        
        del admin_states[user_id]
        
        await update.message.reply_text(
            ADMIN_MESSAGES["saved"],
            reply_markup=get_texts_keyboard()
        )
    
    elif state == AdminState.CREATE_CHAIN:
        # Создание цепочки
        step = state_data.get("step")
        
        if step == "name":
            state_data["data"]["name"] = text
            state_data["step"] = "code"
            await update.message.reply_text(
                "Шаг 2: Введите код цепочки (латиница, например: coursework_fast):"
            )
        
        elif step == "code":
            state_data["data"]["code"] = text
            state_data["step"] = "milestones"
            await update.message.reply_text(
                """Шаг 3: Определите этапы в формате JSON:
[
  {"name": "Этап 1", "days": 14},
  {"name": "Этап 2", "days": 30}
]"""
            )
        
        elif step == "milestones":
            try:
                milestones = json.loads(text)
                state_data["data"]["milestones"] = milestones
                
                # Сохраняем цепочку
                await save_milestone_chain(state_data["data"])
                
                del admin_states[user_id]
                
                await update.message.reply_text(
                    ADMIN_MESSAGES["chain_created"].format(
                        name=state_data["data"]["name"],
                        steps_count=len(milestones),
                        work_types=state_data["data"]["code"]
                    ),
                    reply_markup=get_chains_keyboard()
                )
            except json.JSONDecodeError:
                await update.message.reply_text("❌ Ошибка в JSON. Проверьте формат и попробуйте снова.")
    
    elif state == AdminState.CREATE_CODE:
        # Создание кода доступа
        step = state_data.get("step")
        
        if step == "code":
            state_data["data"]["code"] = text.upper()
            state_data["step"] = "description"
            await update.message.reply_text("Шаг 2: Описание кода (для чего он):")
        
        elif step == "description":
            state_data["data"]["description"] = text
            state_data["step"] = "max_uses"
            await update.message.reply_text("Шаг 3: Макс. использований (число или 0 для безлимита):")
        
        elif step == "max_uses":
            try:
                max_uses = int(text)
                state_data["data"]["max_uses"] = max_uses
                
                # Сохраняем код
                code = await save_access_code(state_data["data"])
                
                del admin_states[user_id]
                
                await update.message.reply_text(
                    ADMIN_MESSAGES["code_created"].format(
                        code=state_data["data"]["code"],
                        expires="без ограничений",
                        max_uses=max_uses if max_uses > 0 else "∞"
                    ),
                    reply_markup=get_codes_keyboard()
                )
            except ValueError:
                await update.message.reply_text("❌ Введите число.")

async def save_milestone_chain(data: Dict[str, Any]) -> bool:
    """Сохранение цепочки в конфиг"""
    config_file = CONFIG_DIR / "milestone_chains.yaml"
    
    chains = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            chains = yaml.safe_load(f) or {}
    
    code = data["code"]
    chains[code] = {
        "name": data["name"],
        "milestones": data["milestones"]
    }
    
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(chains, f, allow_unicode=True, default_flow_style=False)
    
    return True

async def save_access_code(data: Dict[str, Any]) -> str:
    """Сохранение кода доступа в БД"""
    # TODO: Реализовать сохранение в БД
    return data["code"]

# =============================================================================
# ЗАПУСК
# =============================================================================

def main():
    """Запуск админ-панели"""
    if not BOT_TOKEN:
        print("Ошибка: Установите переменную TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    if TEACHER_TELEGRAM_ID == 0:
        print("Ошибка: Установите переменную TEACHER_TELEGRAM_ID")
        sys.exit(1)
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🎛️ DigitalTutor Admin Panel запущена!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
