"""
DigitalTutor Bot - AI Review Handler (Cerebras via SOCKS5 Proxy)
Generates AI-powered reviews for student works
Proxy: 81.200.157.139:1080 (Germany) -> bypasses RU block
"""
import logging
import uuid
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select, update
from datetime import datetime
import httpx
import os

from bot.models import AsyncSessionContext, StudentWork, File
from bot.services.minio_service import download_file_to_temp
from bot.keyboards import get_admin_menu

logger = logging.getLogger(__name__)
router = Router()

ADMIN_IDS = [502621151]

# SOCKS5 Proxy config for bypassing geo-restrictions
PROXY_URL = "socks5://81.200.157.139:1080"

# AI Review prompts - UPDATED with approved structure
SMALL_REVIEW_PROMPT = """Ты - опытный рецензент студенческих работ. Проанализируй работу и дай КРАТКУЮ рецензию (300-500 знаков).

ФОРМАТ ОТВЕТА (строго соблюдай):
📊 ОЦЕНКИ
• Структура: X/10
• Соответствие теме: X/10
• Методология: X/10
• Уникальность: X%
• ИИ-редакция: X/10

⚠️ ИСПРАВИТЬ:
1. [конкретный пункт]
2. [конкретный пункт]

💡 ВЕРДИКТ: [1 предложение]

Работа для анализа:
{content}

Важно: используй только цифры от 0-10 для оценок, X% для уникальности. Будь краток и конкретен."""

BIG_REVIEW_PROMPT = """Ты - профессиональный научный рецензент (peer reviewer). Проведи полное методологическое рецензирование работы по критериям HESR (Holistic Editor's Scoring Rubric).

ФОРМАТ ОТВЕТА (строго соблюдай структуру):
═══════════════════════════════════════
📋 ОБЩАЯ ОЦЕНКА (HESR: X/5)
═══════════════════════════════════════
[2-3 предложения: соответствие теме, уровень работы (бакалавр/магистратура), основной вывод]

═══════════════════════════════════════
📊 КРИТЕРИИ ОЦЕНКИ
═══════════════════════════════════════
• Оригинальность и новизна: X/10 — [обоснование]
• Методологическая строгость: X/10 — [обоснование]
• Вклад в знания: X/10 — [обоснование]
• Аргументация и логика: X/10 — [обоснование]
• Соответствие стандартам: X/10 — [обоснование]
• Уникальность текста: X%
• Видимость ИИ: X/10

═══════════════════════════════════════
✅ СИЛЬНЫЕ СТОРОНЫ
═══════════════════════════════════════
• [конкретное достоинство с указанием раздела]
• [конкретное достоинство]

═══════════════════════════════════════
⚠️ КРИТИЧЕСКИЕ ЗАМЕЧАНИЯ
═══════════════════════════════════════
1. [раздел]: [конкретная проблема + рекомендация по исправлению]
2. [раздел]: [конкретная проблема + рекомендация по исправлению]
3. [раздел]: [конкретная проблема + рекомендация по исправлению]

═══════════════════════════════════════
🎯 РЕКОМЕНДАЦИИ РЕЦЕНЗЕНТА
═══════════════════════════════════════
[3-4 предложения с конкретными actionable рекомендациями по улучшению работы]

═══════════════════════════════════════
📌 РЕШЕНИЕ: [Принять / Минорные правки / Мажорные правки / Отклонить]
═══════════════════════════════════════

Работа для рецензирования:
{content}

Важно: 
- Будь объективен и конструктивен
- Указывай конкретные разделы с проблемами
- Давай actionable рекомендации (что именно исправить)
- HESR оценивай по 5-балльной шкале (5=отлично, 1=неприемлемо)"""

# Store pending AI reviews: {message_id: {work_id, review_text}}
pending_ai_reviews = {}


async def extract_text_from_file(file_path: str, mime_type: str) -> str:
    """Extract text from file (docx, pdf, txt)"""
    try:
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_path.endswith('.docx'):
            try:
                import docx2txt
                return docx2txt.process(file_path)
            except ImportError:
                logger.error("docx2txt not installed")
                return "[Ошибка: не удалось извлечь текст из DOCX]"
        
        elif mime_type == "text/plain" or file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif mime_type == "application/pdf" or file_path.endswith('.pdf'):
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                logger.error("PyPDF2 not installed")
                return "[Ошибка: не удалось извлечь текст из PDF]"
        
        else:
            return "[Неподдерживаемый формат файла]"
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return f"[Ошибка извлечения текста: {e}]"


async def call_cerebras_api(prompt: str, model: str = "llama3.1-8b") -> str:
    """Call Cerebras API via SOCKS5 proxy (bypasses RU geo-block)"""
    api_key = os.getenv('CEREBRAS_API_KEY', '')
    if not api_key:
        return "[Ошибка: CEREBRAS_API_KEY не настроен]"
    
    try:
        # Use SOCKS5 proxy for Cerebras API
        proxy_config = {
            "http://": PROXY_URL,
            "https://": PROXY_URL
        }
        
        async with httpx.AsyncClient(timeout=180.0, proxy=proxy_config) as client:
            response = await client.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            elif response.status_code == 429:
                return "[Лимит Cerebras превышен (14,400/день). Попробуйте завтра.]"
            else:
                logger.error(f"Cerebras API error: {response.status_code} - {response.text}")
                return f"[Ошибка Cerebras API: {response.status_code}]"
    except Exception as e:
        logger.error(f"Error calling Cerebras API: {e}")
        return f"[Ошибка соединения: {e}]"


async def call_ai_api(prompt: str, review_type: str = "small") -> str:
    """Call AI API via Cerebras through SOCKS5 proxy"""
    return await call_cerebras_api(prompt, model="llama3.1-8b")


@router.callback_query(F.data.startswith("ai_review:"))
async def start_ai_review(callback_query: CallbackQuery):
    """Show AI review options (small/big)"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Нет доступа", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Маленькая рецензия", callback_data=f"ai_small:{work_id}")],
        [InlineKeyboardButton(text="📄 Большая рецензия", callback_data=f"ai_big:{work_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_work:{work_id}")]
    ])
    
    await callback_query.message.edit_text(
        "🤖 <b>AI-рецензия</b>\n\n"
        "Выберите тип рецензии:\n\n"
        "📝 <b>Маленькая:</b> Краткий анализ с оценками и замечаниями\n"
        "📄 <b>Большая:</b> Полное научное рецензирование (HESR)\n\n"
        "<i>⚡ Cerebras через Germany Proxy (14,400 запросов/день)</i>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback_query.answer()


@router.callback_query(F.data.startswith("ai_small:"))
async def generate_small_review(callback_query: CallbackQuery):
    """Generate small AI review"""
    await generate_ai_review(callback_query, "small")


@router.callback_query(F.data.startswith("ai_big:"))
async def generate_big_review(callback_query: CallbackQuery):
    """Generate big AI review"""
    await generate_ai_review(callback_query, "big")


async def generate_ai_review(callback_query: CallbackQuery, review_type: str):
    """Generate AI review for work"""
    work_id_str = callback_query.data.split(":")[1]
    work_id = uuid.UUID(work_id_str)
    
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Show loading status IN PLACE
    if review_type == "small":
        loading_text = "⏳ <b>Генерирую краткую рецензию...</b>\n\n<i>Cerebras Llama 3.1 через Germany Proxy...</i>"
        review_title = "📝 Краткая рецензия"
    else:
        loading_text = "⏳ <b>Провожу научное рецензирование...</b>\n\n<i>HESR методология через Cerebras...</i>"
        review_title = "📄 Полное рецензирование"
    
    await callback_query.message.edit_text(
        loading_text,
        parse_mode="HTML"
    )
    await callback_query.answer()
    
    async with AsyncSessionContext() as session:
        result = await session.execute(
            select(StudentWork).where(StudentWork.id == work_id)
        )
        work = result.scalar_one_or_none()
        
        if not work:
            await callback_query.message.edit_text(
                "❌ <b>Работа не найдена</b>",
                parse_mode="HTML"
            )
            return
        
        # Get files
        result = await session.execute(
            select(File).where(File.work_id == work_id)
        )
        files = result.scalars().all()
        
        if not files:
            await callback_query.message.edit_text(
                "❌ <b>Нет файлов для анализа</b>\n\n"
                "Загрузите файл работы перед генерацией AI-рецензии.",
                parse_mode="HTML"
            )
            return
        
        # Extract text from first file
        file_record = files[0]
        temp_path = await download_file_to_temp(file_record.filename)
        
        if not temp_path:
            await callback_query.message.edit_text(
                "❌ <b>Ошибка загрузки файла</b>",
                parse_mode="HTML"
            )
            return
        
        try:
            # Extract text
            file_content = await extract_text_from_file(temp_path, file_record.mime_type)
            
            # Limit content length
            if len(file_content) > 15000:
                file_content = file_content[:15000] + "\n\n[Текст обрезан для анализа]"
            
            # Generate prompt
            if review_type == "small":
                prompt = SMALL_REVIEW_PROMPT.format(content=file_content)
            else:
                prompt = BIG_REVIEW_PROMPT.format(content=file_content)
            
            # Call AI via SOCKS5 proxy
            ai_response = await call_ai_api(prompt, review_type)
            
            if ai_response.startswith("[Ошибка"):
                await callback_query.message.edit_text(
                    f"❌ {ai_response}\n\n"
                    f"Попробуйте позже или обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Store review for sharing
            review_data = {
                'work_id': work_id,
                'review_text': ai_response,
                'review_type': review_type,
                'work_title': work.title
            }
            
            # Build review text
            review_text = f"""{review_title}

<b>Работа:</b> {work.title}

{ai_response}

---
⚠️ <i>Это AI-генерированная рецензия. Проверьте перед отправкой студенту.</i>"""
            
            # Store message ID for sharing
            msg_id = callback_query.message.message_id
            pending_ai_reviews[msg_id] = review_data
            
            # Add action buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Поделиться с автором", callback_data=f"share_review:{msg_id}")],
                [InlineKeyboardButton(text="◀️ К работе", callback_data=f"admin_work:{work_id}")]
            ])
            
            # EDIT CURRENT MESSAGE (or send new if too long)
            if len(review_text) > 4000:
                # Split into two messages
                await callback_query.message.edit_text(
                    review_text[:4000] + "\n\n[Продолжение в следующем сообщении...]",
                    parse_mode="HTML"
                )
                second_msg = await callback_query.message.answer(
                    review_text[4000:],
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                # Update stored message ID for sharing
                pending_ai_reviews[second_msg.message_id] = review_data
            else:
                await callback_query.message.edit_text(
                    review_text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            
        finally:
            # Cleanup
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass


@router.callback_query(F.data.startswith("share_review:"))
async def share_review_with_student(callback_query: CallbackQuery):
    """Share AI review with student"""
    msg_id = int(callback_query.data.split(":")[1])
    
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Нет доступа", show_alert=True)
        return
    
    review_data = pending_ai_reviews.get(msg_id)
    if not review_data:
        await callback_query.answer("❌ Данные рецензии не найдены", show_alert=True)
        return
    
    # Save to database as teacher_comment
    async with AsyncSessionContext() as session:
        await session.execute(
            update(StudentWork)
            .where(StudentWork.id == review_data['work_id'])
            .values(
                teacher_comment=f"[AI-рецензия]\n\n{review_data['review_text']}",
                teacher_reviewed_at=datetime.utcnow()
            )
        )
        await session.commit()
    
    # Update message text to show it's shared
    current_text = callback_query.message.text or callback_query.message.caption or ""
    new_text = current_text + "\n\n✅ <b>Отправлено студенту</b>"
    
    await callback_query.message.edit_text(
        new_text[:4000],
        parse_mode="HTML"
    )
    await callback_query.answer("✅ Рецензия отправлена студенту")


@router.callback_query(F.data.startswith("delete_review:"))
async def delete_ai_review(callback_query: CallbackQuery):
    """Delete AI review message - go back to work details"""
    msg_id = int(callback_query.data.split(":")[1])
    
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Нет доступа", show_alert=True)
        return
    
    if msg_id in pending_ai_reviews:
        work_id = pending_ai_reviews[msg_id]['work_id']
        del pending_ai_reviews[msg_id]
        # Go back to work details
        from bot.handlers.works import show_admin_work_details
        await show_admin_work_details(callback_query, work_id)
    else:
        await callback_query.message.delete()
    
    await callback_query.answer()
