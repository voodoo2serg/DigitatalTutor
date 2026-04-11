"""
DigitalTutor Bot - Admin Settings Handler
Управление настройками AI-провайдеров через Telegram
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import config
from bot.services.ai_service import ai_service
import os

logger = logging.getLogger(__name__)
router = Router()


class SettingsStates(StatesGroup):
    waiting_cerebras_key = State()
    waiting_openrouter_key = State()
    waiting_huggingface_key = State()
    waiting_ollama_url = State()
    waiting_ollama_model = State()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    """Show settings menu (admin only)"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Доступ только для администраторов.")
        return
    
    await show_ai_settings(message)


async def show_ai_settings(message_or_callback):
    """Show AI provider settings"""
    provider_info = ai_service.get_provider_info()
    active_providers = ai_service.get_active_providers()
    
    text = "⚙️ <b>Настройки AI-провайдеров</b>\n\n"
    text += f"🟢 Активных провайдеров: {len(active_providers)}\n"
    
    provider_names = {
        "cerebras": ("⚡ Cerebras", "Быстрый инференс"),
        "openrouter": ("🌐 OpenRouter", "Резервный провайдер"),
        "ollama": ("🦙 Ollama", "Локальная модель"),
        "huggingface": ("🤗 HuggingFace", "Open Source модели"),
    }
    
    for key, (display_name, description) in provider_names.items():
        info = provider_info.get(key, {})
        is_active = info.get("is_active", False)
        has_key = info.get("has_api_key", False)
        model = info.get("default_model", "N/A")
        
        status = "✅" if (has_key or key == "ollama") else "❌"
        text += f"\n{status} <b>{display_name}</b>"
        text += f"\n   {description}"
        text += f"\n   Модель: <code>{model}</code>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Cerebras API Key", callback_data="set_cerebras_key"),
            InlineKeyboardButton(text="🌐 OpenRouter API Key", callback_data="set_openrouter_key"),
        ],
        [
            InlineKeyboardButton(text="🤗 HuggingFace API Key", callback_data="set_huggingface_key"),
            InlineKeyboardButton(text="🦙 Ollama", callback_data="set_ollama"),
        ],
        [
            InlineKeyboardButton(text="🔄 Перезагрузить провайдеры", callback_data="reload_providers"),
        ],
        [InlineKeyboardButton(text="📊 Статус системы", callback_data="system_status")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")],
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        try:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await message_or_callback.answer()
        except Exception:
            await message_or_callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "set_cerebras_key")
async def prompt_cerebras_key(callback: CallbackQuery, state: FSMContext):
    current = "•••" + os.getenv("CEREBRAS_API_KEY", "")[-4:] if os.getenv("CEREBRAS_API_KEY") else "не задан"
    await callback.message.answer(
        f"⚡ <b>Cerebras API Key</b>\n\nТекущий: <code>{current}</code>\n\n"
        f"Отправьте новый API ключ (или «отмена»):",
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_cerebras_key)
    await callback.answer()


@router.callback_query(F.data == "set_openrouter_key")
async def prompt_openrouter_key(callback: CallbackQuery, state: FSMContext):
    current = "•••" + os.getenv("OPENROUTER_API_KEY", "")[-4:] if os.getenv("OPENROUTER_API_KEY") else "не задан"
    await callback.message.answer(
        f"🌐 <b>OpenRouter API Key</b>\n\nТекущий: <code>{current}</code>\n\n"
        f"Отправьте новый API ключ (или «отмена»):",
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_openrouter_key)
    await callback.answer()


@router.callback_query(F.data == "set_huggingface_key")
async def prompt_huggingface_key(callback: CallbackQuery, state: FSMContext):
    current = "•••" + os.getenv("HUGGINGFACE_API_KEY", "")[-4:] if os.getenv("HUGGINGFACE_API_KEY") else "не задан"
    await callback.message.answer(
        f"🤗 <b>HuggingFace API Key</b>\n\nТекущий: <code>{current}</code>\n\n"
        f"Отправьте новый API ключ (или «отмена»):",
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_huggingface_key)
    await callback.answer()


@router.callback_query(F.data == "set_ollama")
async def prompt_ollama_settings(callback: CallbackQuery, state: FSMContext):
    ollama_url = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Изменить URL", callback_data="set_ollama_url")],
        [InlineKeyboardButton(text="🤖 Изменить модель", callback_data="set_ollama_model")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="show_settings_back")],
    ])
    
    await callback.message.edit_text(
        f"🦙 <b>Ollama (локальная модель)</b>\n\n"
        f"🔗 URL: <code>{ollama_url}</code>\n"
        f"🤖 Модель: <code>{ollama_model}</code>\n\n"
        f"Ollama работает локально и не требует API ключа.\n"
        f"Убедитесь что Ollama запущена и модель скачана.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "set_ollama_url")
async def prompt_ollama_url(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        f"🦙 Отправьте URL Ollama (например, http://ollama:11434):\n\n"
        f"Текущий: <code>{os.getenv('OLLAMA_HOST', 'http://ollama:11434')}</code>",
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_ollama_url)
    await callback.answer()


@router.callback_query(F.data == "set_ollama_model")
async def prompt_ollama_model(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🦙 Отправьте название модели Ollama (например, gemma3:4b):\n\n"
        "Текущий: <code>" + os.getenv("OLLAMA_MODEL", "gemma3:4b") + "</code>",
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_ollama_model)
    await callback.answer()


@router.callback_query(F.data == "reload_providers")
async def reload_providers(callback: CallbackQuery):
    """Reload AI providers from environment"""
    try:
        from bot.services.ai_service import init_ai_service
        # Clear existing providers
        ai_service.providers.clear()
        # Reinitialize
        init_ai_service()
        
        active = ai_service.get_active_providers()
        await callback.message.answer(
            f"✅ AI-провайдеры перезагружены\n\n"
            f"🟢 Активных: {', '.join(active) if active else 'нет'}",
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {e}", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "system_status")
async def show_system_status(callback: CallbackQuery):
    """Show system status"""
    import asyncio
    
    provider_info = ai_service.get_provider_info()
    
    text = "📊 <b>Статус системы</b>\n\n"
    text += "🤖 <b>AI Провайдеры:</b>\n"
    
    for name, info in provider_info.items():
        status = "🟢" if info.get("has_api_key") or name == "ollama" else "🔴"
        text += f"{status} {name}: {'активен' if info.get('has_api_key') or name == 'ollama' else 'нет ключа'}\n"
    
    text += "\n📋 <b>Планировщик:</b>\n"
    try:
        from bot.services.scheduler import _scheduler
        if _scheduler and _scheduler.running:
            text += "🟢 Напоминания о дедлайнах: активны\n"
        else:
            text += "🔴 Напоминания о дедлайнах: неактивны\n"
    except Exception:
        text += "⚪ Напоминания: APScheduler не установлен\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="show_settings_back")],
    ])
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "show_settings_back")
async def back_to_settings(callback: CallbackQuery):
    await show_ai_settings(callback)


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    from bot.keyboards import get_admin_menu
    await callback.message.answer("📋 Админ-меню:", reply_markup=get_admin_menu())
    await callback.message.delete()
    await callback.answer()


# State handlers for text input
settings_text_router = Router()


@settings_text_router.message(SettingsStates.waiting_cerebras_key)
async def save_cerebras_key(message: Message, state: FSMContext):
    key = message.text.strip()
    if key.lower() in ['отмена', 'cancel']:
        await state.clear()
        await message.answer("❌ Отменено", reply_markup=get_cancel_or_admin_menu())
        return
    
    ai_service.register_provider("cerebras", key, "https://api.cerebras.ai", "llama-4-scout-17b-16e-instruct", True)
    await message.answer("✅ Cerebras API Key обновлён!\n\nДля постоянного сохранения добавьте ключ в .env:\n<code>CEREBRAS_API_KEY={key}</code>", parse_mode="HTML")
    await state.clear()


@settings_text_router.message(SettingsStates.waiting_openrouter_key)
async def save_openrouter_key(message: Message, state: FSMContext):
    key = message.text.strip()
    if key.lower() in ['отмена', 'cancel']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    ai_service.register_provider("openrouter", key, "https://openrouter.ai/api", "openai/gpt-4o-mini", True)
    await message.answer("✅ OpenRouter API Key обновлён!\n\nДля постоянного сохранения:\n<code>OPENROUTER_API_KEY={key}</code>", parse_mode="HTML")
    await state.clear()


@settings_text_router.message(SettingsStates.waiting_huggingface_key)
async def save_huggingface_key(message: Message, state: FSMContext):
    key = message.text.strip()
    if key.lower() in ['отмена', 'cancel']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    ai_service.register_provider("huggingface", key, "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct", "meta-llama/Meta-Llama-3-8B-Instruct", True)
    await message.answer("✅ HuggingFace API Key обновлён!\n\nДля постоянного сохранения:\n<code>HUGGINGFACE_API_KEY={key}</code>", parse_mode="HTML")
    await state.clear()


@settings_text_router.message(SettingsStates.waiting_ollama_url)
async def save_ollama_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if url.lower() in ['отмена', 'cancel']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    if "ollama" in ai_service.providers:
        ai_service.providers["ollama"]["base_url"] = url
    await message.answer(f"✅ Ollama URL обновлён: {url}\n\nДля постоянного сохранения:\n<code>OLLAMA_HOST={url}</code>", parse_mode="HTML")
    await state.clear()


@settings_text_router.message(SettingsStates.waiting_ollama_model)
async def save_ollama_model(message: Message, state: FSMContext):
    model = message.text.strip()
    if model.lower() in ['отмена', 'cancel']:
        await state.clear()
        await message.answer("❌ Отменено")
        return
    
    if "ollama" in ai_service.providers:
        ai_service.providers["ollama"]["default_model"] = model
    await message.answer(f"✅ Ollama модель обновлена: {model}\n\nДля постоянного сохранения:\n<code>OLLAMA_MODEL={model}</code>", parse_mode="HTML")
    await state.clear()


def get_cancel_or_admin_menu():
    from bot.keyboards import get_admin_menu
    return get_admin_menu()
