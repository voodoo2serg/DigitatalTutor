"""
DigitalTutor Bot v4.0 - Main Entry Point
"""
import logging
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot token from env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def main():
    """Главная функция запуска бота"""
    logger.info("Starting DigitalTutor Bot v4.0...")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    # Initialize bot and dispatcher
    bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Import handlers
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
    )
    
    # Register routers
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
    
    logger.info("Bot started successfully!")
    
    # Start polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
