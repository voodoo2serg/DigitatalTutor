"""
DigitalTutor Bot v4.0 - Configuration
Конфигурация бота
"""
import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Конфигурация бота"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Yandex Disk
    YANDEX_DISK_TOKEN: str = os.getenv("YANDEX_DISK_TOKEN", "")
    
    # API
    API_BASE_URL: str = "http://digitatal-backend:8000/api/v1"
    
    # Admin IDs
    ADMIN_IDS: List[int] = None
    
    # Throttling
    THROTTLING_DELAY: int = int(os.getenv("THROTTLING_DELAY", "15"))
    
    def __post_init__(self):
        if self.ADMIN_IDS is None:
            self.ADMIN_IDS = [502621151]  # @voodoo_cap


# Throttling для массовых рассылок (в секундах)
THROTTLING_DELAY = int(os.getenv("THROTTLING_DELAY", "15"))  # по умолчанию 15 сек

# Инициализация конфигурации
config = Config()

# Роли студентов
STUDENT_ROLES = {
    "vkr": {
        "name": "ВКР",
        "description": "Выпускная квалификационная работа (бакалавр/магистр)",
        "plan_points": [
            {"num": 1, "name": "Предзащита", "description": "Предварительная защита работы"},
            {"num": 2, "name": "Финальная защита", "description": "Окончательная защита ВКР"}
        ]
    },
    "aspirant": {
        "name": "Аспирант",
        "description": "Аспирантские исследования",
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
        "description": "ВКР с публикацией статьи",
        "plan_points": [
            {"num": 1, "name": "Научная статья", "description": "Написание и публикация статьи"},
            {"num": 2, "name": "Текст ВКР", "description": "Подготовка текста ВКР"},
            {"num": 3, "name": "Защита", "description": "Предзащита и финальная защита"}
        ]
    },
    "article_guide": {
        "name": "Руководство по статье",
        "description": "Руководство по написанию статьи",
        "plan_points": [
            {"num": 1, "name": "Выбор темы", "description": "Определение темы и журнала"},
            {"num": 2, "name": "Написание", "description": "Подготовка текста статьи"},
            {"num": 3, "name": "Публикация", "description": "Отправка в журнал, рецензирование"}
        ]
    },
    "work_guide": {
        "name": "Руководство по работе",
        "description": "Руководство по написанию работы",
        "plan_points": [
            {"num": 1, "name": "Тема и план", "description": "Утверждение темы и плана работы"},
            {"num": 2, "name": "Написание", "description": "Работа над текстом"},
            {"num": 3, "name": "Завершение", "description": "Финальная проверка и сдача"}
        ]
    },
    "other": {
        "name": "Другой проект",
        "description": "Иной научный проект",
        "plan_points": [
            {"num": 1, "name": "Постановка задачи", "description": "Определение целей и задач"},
            {"num": 2, "name": "Выполнение", "description": "Работа над проектом"},
            {"num": 3, "name": "Результат", "description": "Подготовка итогового результата"}
        ]
    }
}

# Типы работ для сдачи
WORK_TYPES = {
    "1": ("Курсовая работа", "coursework"),
    "2": ("ВКР (Бакалавр)", "vkr_bachelor"),
    "3": ("ВКР (Магистр)", "vkr_master"),
    "4": ("Научная статья", "article"),
    "5": ("Реферат", "essay"),
    "6": ("Проект", "project"),
    "7": ("Другое", "other"),
}

# Статусы работ
STATUS_INFO = {
    "draft": {"emoji": "📝", "name": "Черновик"},
    "submitted": {"emoji": "📤", "name": "Отправлена"},
    "in_review": {"emoji": "👀", "name": "На проверке"},
    "revision_required": {"emoji": "🔄", "name": "Требует доработки"},
    "accepted": {"emoji": "✅", "name": "Принята"},
    "rejected": {"emoji": "❌", "name": "Отклонена"},
}

# Шаблоны автоматических сообщений
AUTO_MESSAGES = {
    "welcome": """🎓 Добро пожаловать в DigitalTutor, {name}!

Вы успешно зарегистрированы с ролью: {role}

📋 <b>Ваш план работ:</b>
{plan}

Начните с «📋 Мои работы» или «➕ Сдать работу»""",

    "work_submitted": """✅ Работа успешно сдана!

📝 <b>{title}</b>
📊 Статус: На проверке

Ваша работа поставлена на проверку. Результаты будут доступны в разделе «📋 Мои работы».

Вы получите уведомление, когда проверка будет завершена.""",

    "deadline_3days": """⏰ <b>Напоминание о дедлайне</b>

У вас есть несданная работа:
📝 {title}
📅 Дедлайн: {deadline} (через 3 дня)

Не забудьте сдать работу вовремя!""",

    "deadline_tomorrow": """🚨 <b>Дедлайн завтра!</b>

📝 {title}
📅 Дедлайн: {deadline}

Срочно завершите работу и сдайте её через бота!""",

    "review_complete": """📊 <b>Результаты проверки</b>

📝 {title}
✅ Статус: {status}

{comment}

Подробности в разделе «📋 Мои работы»""",

    "inactive_7days": """👋 <b>Давно не виделись!</b>

{student_name}, вы не заходили в бот 7 дней.

У вас {works_count} работ{ending} в системе.
Проверьте статус в разделе «📊 Статус»

Если нужна помощь — нажмите «❓ Помощь»""",

    "thanks_reply": """😊 Всегда пожалуйста! {name}, я здесь, чтобы помочь вам с учёбой.

Если будут вопросы — обращайтесь через «💬 Написать руководителю»""",

    "help_reply": """🤝 Конечно помогу, {name}!

Что вас интересует?
• Как сдать работу — нажмите «➕ Сдать работу»
• Проверить статус — «📊 Статус»
• Задать вопрос — «💬 Написать руководителю»

Или опишите ваш вопрос подробнее 👇""",
}
