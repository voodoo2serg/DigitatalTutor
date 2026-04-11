"""
DigitalTutor Bot - AI Review Handler
AI-рецензирование работ с мультипровайдерной поддержкой
"""
import logging
import uuid
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, update

from bot.config import config
from bot.keyboards import get_admin_menu, get_cancel_menu
from bot.services.ai_service import ai_service

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("ai_review:"))
async def start_ai_review(callback: CallbackQuery):
    """Запустить AI-рецензию работы"""
    work_id_str = callback.data.split(":")[1]

    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ У вас нет доступа.", show_alert=True)
        return

    await callback.answer("🤖 Запускаю AI-анализ...", show_alert=False)
    await callback.message.edit_text(
        "⏳ <b>AI-анализ работы</b>\n\n"
        "Анализирую работу по трём критериям:\n"
        "1. 📊 Оригинальность текста\n"
        "2. 🏗️ Структура работы\n"
        "3. 📝 Оформление (ГОСТ)\n\n"
        "⏱ Это может занять 30-60 секунд...",
        parse_mode="HTML"
    )

    try:
        from bot.models import AsyncSessionContext, StudentWork, File

        async with AsyncSessionContext() as session:
            work_id = uuid.UUID(work_id_str)
            result = await session.execute(
                select(StudentWork).where(StudentWork.id == work_id)
            )
            work = result.scalar_one_or_none()

            if not work:
                await callback.message.edit_text("❌ Работа не найдена", parse_mode="HTML")
                return

            # Get the file
            file_result = await session.execute(
                select(File).where(File.work_id == work_id)
            )
            files = file_result.scalars().all()

            if not files:
                await callback.message.edit_text(
                    "❌ Нет файлов для анализа",
                    parse_mode="HTML"
                )
                return

            # Read file content
            import os
            text_content = ""
            for f in files:
                if f.storage_path and os.path.exists(f.storage_path):
                    try:
                        with open(f.storage_path, 'r', encoding='utf-8', errors='ignore') as file:
                            text_content += file.read() + "\n"
                    except Exception as e:
                        logger.error(f"Failed to read file {f.filename}: {e}")
                elif f.ai_extracted_text:
                    text_content += f.ai_extracted_text + "\n"

            if not text_content.strip():
                await callback.message.edit_text(
                    "❌ Не удалось извлечь текст из файлов. "
                    "Поддерживаются текстовые форматы (.txt, .md, .py и т.д.)",
                    parse_mode="HTML"
                )
                return

            # Run analysis for each skill
            skills = [
                ("antiplagiarism", "Проанализируй текст на признаки плагиата и AI-генерации. Оцени оригинальность от 0 до 100."),
                ("structure", "Проанализируй структуру научной работы: введение, основная часть, заключение, список литературы. Оценка от 0 до 100."),
                ("formatting", "Проверь соответствие оформления требованиям: структура заголовков, абзацы, нумерация. Оценка от 0 до 100."),
            ]

            analysis_results = {}
            total_tokens = 0

            for skill_name, prompt in skills:
                try:
                    result_ai = await ai_service.analyze_text(text_content, prompt, skill_name)
                    if result_ai and "result" in result_ai:
                        analysis_results[skill_name] = result_ai["result"]
                        total_tokens += result_ai.get("tokens_used", 0)
                    else:
                        analysis_results[skill_name] = {
                            "score": 0,
                            "assessment": "Анализ недоступен",
                            "findings": [],
                            "recommendations": [],
                        }
                except Exception as e:
                    logger.error(f"AI analysis failed for {skill_name}: {e}")
                    analysis_results[skill_name] = {
                        "score": 0,
                        "assessment": f"Ошибка: {e}",
                        "findings": [],
                        "recommendations": [],
                    }

            # Update work in DB
            plag = analysis_results.get("antiplagiarism", {}).get("score", 0)
            struct = analysis_results.get("structure", {}).get("score", 0)
            fmt = analysis_results.get("formatting", {}).get("score", 0)

            await session.execute(
                update(StudentWork)
                .where(StudentWork.id == work_id)
                .values(
                    ai_plagiarism_score=plag,
                    ai_structure_score=struct,
                    ai_formatting_score=fmt,
                    ai_analysis_json=analysis_results,
                    updated_at=__import__('datetime').datetime.utcnow()
                )
            )

            # Format result
            provider_info = ai_service.get_provider_info()
            active_providers = [name for name, info in provider_info.items() if info.get("has_api_key")]
            provider_str = ", ".join(active_providers) if active_providers else "Нет"

            plag_emoji = "🟢" if plag >= 70 else "🟡" if plag >= 40 else "🔴"
            struct_emoji = "🟢" if struct >= 70 else "🟡" if struct >= 40 else "🔴"
            fmt_emoji = "🟢" if fmt >= 70 else "🟡" if fmt >= 40 else "🔴"

            text = f"""🤖 <b>Результаты AI-анализа</b>

📊 Оригинальность: {plag_emoji} {plag}/100
{'   ' + analysis_results.get('antiplagiarism', {}).get('assessment', '')[:100]}

🏗️ Структура: {struct_emoji} {struct}/100
{'   ' + analysis_results.get('structure', {}).get('assessment', '')[:100]}

📝 Оформление: {fmt_emoji} {fmt}/100
{'   ' + analysis_results.get('formatting', {}).get('assessment', '')[:100]}

💻 Провайдер: {provider_str}
📝 Токенов: {total_tokens}"""

            # Add findings if available
            all_findings = []
            all_recommendations = []
            for skill_name, data in analysis_results.items():
                if isinstance(data, dict):
                    all_findings.extend(data.get("findings", [])[:3])
                    all_recommendations.extend(data.get("recommendations", [])[:3])

            if all_findings:
                text += "\n\n🔍 <b>Найденные проблемы:</b>"
                for finding in all_findings[:5]:
                    text += f"\n• {finding}"

            if all_recommendations:
                text += "\n\n💡 <b>Рекомендации:</b>"
                for rec in all_recommendations[:5]:
                    text += f"\n• {rec}"

            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✍️ Написать рецензию", callback_data=f"add_review:{work_id_str}"),
                    InlineKeyboardButton(text="⭐ Оценить", callback_data=f"grade_work:{work_id_str}")
                ],
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_work:{work_id_str}")]
            ])

            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error(f"AI review failed: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка AI-анализа: {str(e)[:200]}\n\n"
            "Проверьте настройки AI-провайдеров в разделе ⚙️ Настройки",
            parse_mode="HTML"
        )
