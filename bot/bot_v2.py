"""
DigitalTutor Bot v4.0 - Main Entry Point
Telegram-бот для системы DigitalTutor с ReplyKeyboard, планами работ и Яндекс.Диском

Функции:
- Регистрация с выбором роли (ВКР, Аспирант, и др.)
- Планы работы для 6 типов ролей
- Сдача работ с загрузкой на Яндекс.Диск
- Просмотр работ и статусов
- Коммуникация с руководителем
- Авто-коммуникация (шаблоны сообщений)
- AI-рецензии
- Управление студентами
- Массовая рассылка
- Система оценок
"""
import logging
import asyncio
import sys
from pathlib import Path

# Добавляем путь к backend для импорта моделей
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    logger.info("Starting DigitalTutor Bot v4.0...")

    # Проверка токена
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Импорт и регистрация роутеров
    from bot.handlers import (
        start_router,
        registration_router,
        works_router,
        submit_router,
        plan_router,
        communication_router,
        ai_review_router,
        students_router,
        works_review_router,
        mass_messaging_router,
        grade_router,
        review_router,
        admin_settings_router,
        settings_text_router,
    )

    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(works_router)
    dp.include_router(submit_router)
    dp.include_router(plan_router)
    dp.include_router(communication_router)
    dp.include_router(ai_review_router)
    dp.include_router(students_router)
    dp.include_router(works_review_router)
    dp.include_router(mass_messaging_router)
    dp.include_router(grade_router)
    dp.include_router(review_router)
    dp.include_router(admin_settings_router)
    dp.include_router(settings_text_router)

    logger.info("All routers registered successfully!")
    logger.info("Bot started successfully!")

    # Initialize AI service
    try:
        from bot.services.ai_service import init_ai_service
        init_ai_service()
        logger.info("AI Service initialized")
    except Exception as e:
        logger.warning(f"AI Service init failed (non-critical): {e}")

    # Start deadline reminder scheduler
    try:
        from bot.services.scheduler import start_scheduler
        start_scheduler(bot)
        logger.info("Deadline reminder scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler init failed (non-critical): {e}")

    # Запуск polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
