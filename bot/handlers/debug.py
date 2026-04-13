"""Debug handler - временный для диагностики"""
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("start"))
async def debug_start(message: Message):
    """Тестовый обработчик /start"""
    logger.info(f"DEBUG: /start received from {message.from_user.id}")
    await message.answer(f"✅ Бот работает!\nUser ID: {message.from_user.id}\nUsername: @{message.from_user.username}")

@router.message(F.text)
async def debug_any_text(message: Message):
    """Ответ на любой текст"""
    logger.info(f"DEBUG: text received: {message.text[:50]} from {message.from_user.id}")
    await message.answer(f"Echo: {message.text[:100]}")
