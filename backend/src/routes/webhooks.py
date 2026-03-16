"""
Webhooks API Routes
Приём webhook'ов от Telegram и других сервисов
"""

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from src.database import get_db, AsyncSessionLocal
from src.models.schemas import TelegramUpdate

router = APIRouter()
logger = structlog.get_logger()


@router.post("/telegram")
async def telegram_webhook(
    update: TelegramUpdate,
    background_tasks: BackgroundTasks
):
    """
    Обработка webhook от Telegram Bot API

    Обрабатывает:
    - Команды (/start, /help, /status)
    - Текстовые сообщения
    - Документы (файлы)
    - Фото
    - Callback queries (кнопки)
    """
    logger.info(
        "Telegram webhook received",
        update_id=update.update_id
    )

    # Обрабатываем в фоне
    background_tasks.add_task(process_telegram_update, update)

    return {"status": "ok"}


async def process_telegram_update(update: TelegramUpdate):
    """
    Асинхронная обработка обновления от Telegram
    """
    async with AsyncSessionLocal() as db:
        try:
            if update.message:
                await process_message(update.message, db)
            elif update.callback_query:
                await process_callback(update.callback_query, db)
        except Exception as e:
            logger.error("Error processing update", error=str(e))


async def process_message(message, db: AsyncSession):
    """
    Обработка входящего сообщения
    """
    telegram_id = message["from"]["id"]
    text = message.get("text")
    document = message.get("document")

    # Регистрируем или находим студента
    student = await get_or_create_student(telegram_id, message["from"], db)

    if text:
        # Обработка команд
        if text.startswith("/"):
            await handle_command(text, student, db)
        else:
            # Обычное сообщение
            await handle_text_message(text, student, db)

    if document:
        # Загрузка файла
        await handle_document(document, student, db)


async def get_or_create_student(telegram_id: int, user_data: dict, db: AsyncSession):
    """
    Получить или создать студента
    """
    from src.routes.students import Student

    query = select(Student).where(Student.telegram_id == telegram_id)
    result = await db.execute(query)
    student = result.scalar_one_or_none()

    if not student:
        # Создаём нового студента
        display_name = user_data.get("first_name", "Студент")
        if user_data.get("last_name"):
            display_name += f" {user_data['last_name']}"

        student = Student(
            telegram_id=telegram_id,
            telegram_username=user_data.get("username"),
            display_name=display_name,
            role="student"
        )
        db.add(student)
        await db.flush()
        await db.refresh(student)

        logger.info(
            "New student registered",
            telegram_id=telegram_id,
            name=display_name
        )

    return student


async def handle_command(text: str, student, db: AsyncSession):
    """
    Обработка команд бота
    """
    command = text.split()[0].lower()

    if command == "/start":
        # Приветствие
        message = f"""
Добро пожаловать, {student.display_name}!

Я — бот для сдачи работ. Вот что я умею:

📄 /submit — сдать работу
📋 /status — мои работы и статусы
📅 /deadlines — мои дедлайны
❓ /help — справка

Просто отправьте мне файл с описанием, и я помогу оформить сдачу.
"""
        # TODO: Отправить сообщение через Telegram API

    elif command == "/status":
        # Показать статус работ
        from src.routes.submissions import Submission
        query = select(Submission).where(
            Submission.student_id == student.id
        ).order_by(Submission.actual_deadline)
        result = await db.execute(query)
        submissions = result.scalars().all()

        if not submissions:
            message = "У вас пока нет активных работ."
        else:
            lines = ["📋 Ваши работы:\n"]
            for sub in submissions:
                lines.append(f"• {sub.title or 'Без названия'} — {sub.status}")
            message = "\n".join(lines)

        # TODO: Отправить сообщение

    elif command == "/deadlines":
        # Показать ближайшие дедлайны
        message = "📅 Ближайшие дедлайны:\n\n(функция в разработке)"
        # TODO: Реализовать

    elif command == "/help":
        message = """
❓ Справка по командам:

/start — начать работу с ботом
/submit — сдать новую работу
/status — статус моих работ
/deadlines — мои дедлайны
/help — эта справка

Для сдачи работы просто отправьте файл с кратким описанием.
"""
        # TODO: Отправить сообщение


async def handle_text_message(text: str, student, db: AsyncSession):
    """
    Обработка текстового сообщения
    """
    # Сохраняем в историю коммуникаций
    from src.routes.students import Student

    # TODO: Сохранить в communications

    logger.info(
        "Text message received",
        telegram_id=student.telegram_id,
        text_preview=text[:50]
    )


async def handle_document(document: dict, student, db: AsyncSession):
    """
    Обработка загруженного файла
    """
    file_id = document["file_id"]
    file_name = document.get("file_name", "unknown")
    file_size = document.get("file_size", 0)

    logger.info(
        "Document received",
        telegram_id=student.telegram_id,
        file_name=file_name,
        file_size=file_size
    )

    # TODO:
    # 1. Скачать файл через Telegram API
    # 2. Вычислить checksum
    # 3. Загрузить в MinIO
    # 4. Создать запись в files
    # 5. Связать с submission (или создать новую)

    # Отправить подтверждение
    message = f"""
✅ Файл получен: {file_name}

Размер: {file_size / 1024:.1f} KB

Для оформления сдачи укажите:
- Тип работы (курсовая, статья, проект...)
- Название/тему
"""
    # TODO: Отправить сообщение


async def process_callback(callback_data: dict, db: AsyncSession):
    """
    Обработка нажатия на inline-кнопку
    """
    data = callback_data.get("data")
    logger.info("Callback received", data=data)

    # TODO: Обработка различных callback'ов


@router.post("/n8n")
async def n8n_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Webhook для интеграции с n8n

    n8n может отправлять события:
    - reminder_sent — напоминание отправлено
    - file_processed — файл обработан
    - ai_analysis_done — AI-анализ завершён
    """
    body = await request.json()
    event_type = body.get("event")

    logger.info("n8n webhook received", event=event_type)

    # TODO: Обработка различных событий

    return {"status": "ok"}


@router.get("/health")
async def webhook_health():
    """
    Health check для webhook'ов
    """
    return {"status": "healthy"}
