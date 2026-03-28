"""
AI Analysis API с интеграцией OpenRouter и HuggingFace
"""
import logging
import httpx
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.models import (
    StudentWork, File, AIAnalysisLog, AIProvider, 
    MessageTemplate, User, Communication
)
from app.api.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()

# ============== AI PROVIDER MANAGEMENT ==============

@router.get("/providers")
async def list_ai_providers(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Список AI провайдеров (без API ключей)"""
    result = await db.execute(select(AIProvider).order_by(AIProvider.provider_name))
    providers = result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "provider_name": p.provider_name,
            "base_url": p.base_url,
            "default_model": p.default_model,
            "is_active": p.is_active,
            "rate_limit_per_minute": p.rate_limit_per_minute,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in providers
    ]


@router.post("/providers")
async def create_ai_provider(
    provider_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Добавить AI провайдера (OpenRouter, HuggingFace)"""
    new_provider = AIProvider(
        id=uuid4(),
        provider_name=provider_data.get("provider_name"),
        api_key=provider_data.get("api_key"),
        base_url=provider_data.get("base_url"),
        default_model=provider_data.get("default_model", "openai/gpt-4o-mini"),
        is_active=provider_data.get("is_active", True),
        rate_limit_per_minute=provider_data.get("rate_limit_per_minute", 60),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(new_provider)
    await db.commit()
    
    return {
        "id": str(new_provider.id),
        "provider_name": new_provider.provider_name,
        "is_active": new_provider.is_active,
    }


@router.patch("/providers/{provider_name}")
async def update_ai_provider(
    provider_name: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Обновить AI провайдера (ключ, модель, активность)"""
    result = await db.execute(select(AIProvider).where(AIProvider.provider_name == provider_name))
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    if "api_key" in update_data:
        provider.api_key = update_data["api_key"]
    if "default_model" in update_data:
        provider.default_model = update_data["default_model"]
    if "is_active" in update_data:
        provider.is_active = update_data["is_active"]
    if "base_url" in update_data:
        provider.base_url = update_data["base_url"]
    
    provider.updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "success": True,
        "provider_name": provider.provider_name,
        "is_active": provider.is_active,
    }


# ============== AI ANALYSIS ==============

async def analyze_with_openrouter(
    text: str,
    provider: AIProvider,
    skill_name: str,
    prompt_template: str
) -> Dict[str, Any]:
    """Анализ через OpenRouter API"""
    start_time = time.time()
    
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://digitatal.com",
        "X-Title": "DigitalTutor AI Analysis"
    }
    
    prompt = f"""{prompt_template}

Анализируемый текст:
---
{text[:8000]}  # Limit text length
---

Ответь в формате JSON:
{{
    "score": число от 0 до 100,
    "assessment": "краткая оценка",
    "findings": ["список", "найденных", "проблем"],
    "recommendations": ["список", "рекомендаций"]
}}"""
    
    payload = {
        "model": provider.default_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2000,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{provider.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120.0
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if response.status_code != 200:
            logger.error(f"OpenRouter error: {response.text}")
            raise HTTPException(status_code=500, detail="AI analysis failed")
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON response
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = {
                    "score": 50,
                    "assessment": content[:500],
                    "findings": [],
                    "recommendations": []
                }
        
        return {
            "result": result,
            "tokens_used": data.get("usage", {}).get("total_tokens", 0),
            "processing_time_ms": processing_time,
            "provider": provider.provider_name,
            "model": provider.default_model,
        }


@router.post("/analyze/{work_id}")
async def analyze_work_ai(
    work_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Запустить AI анализ работы"""
    # Get work
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Get active AI provider
    result = await db.execute(select(AIProvider).where(AIProvider.is_active == True).limit(1))
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(status_code=500, detail="No active AI provider configured")
    
    # Get file content
    result = await db.execute(
        select(File).where(File.work_id == UUID(work_id)).order_by(desc(File.created_at))
    )
    file = result.scalar_one_or_none()
    
    if not file:
        raise HTTPException(status_code=404, detail="No files found for this work")
    
    # Read file content (assuming text files for now)
    try:
        with open(file.storage_path, 'r', encoding='utf-8', errors='ignore') as f:
            text_content = f.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file content")
    
    # Run analysis for each skill
    skills = [
        ("antiplagiarism", "Проанализируй текст на признаки плагиата и AI-генерации. Оцени оригинальность.", 40),
        ("structure", "Проанализируй структуру научной работы: введение, основная часть, заключение, список литературы.", 30),
        ("formatting", "Проверь соответствие оформления требованиям ГОСТ: шрифты, отступы, нумерация.", 30),
    ]
    
    analysis_results = {}
    total_tokens = 0
    total_cost = 0.0
    
    for skill_name, prompt_template, weight in skills:
        try:
            analysis = await analyze_with_openrouter(text_content, provider, skill_name, prompt_template)
            analysis_results[skill_name] = analysis["result"]
            total_tokens += analysis["tokens_used"]
            
            # Log analysis
            log = AIAnalysisLog(
                id=uuid4(),
                work_id=UUID(work_id),
                file_id=file.id,
                provider_used=analysis["provider"],
                model_used=analysis["model"],
                prompt_sent=prompt_template,
                response_received=json.dumps(analysis["result"]),
                analysis_result=analysis["result"],
                tokens_used=analysis["tokens_used"],
                cost_usd=analysis["tokens_used"] * 0.00001,  # Approximate cost
                processing_time_ms=analysis["processing_time_ms"],
                created_at=datetime.utcnow(),
            )
            db.add(log)
            
        except Exception as e:
            logger.error(f"Analysis error for {skill_name}: {e}")
            analysis_results[skill_name] = {"score": 0, "error": str(e)}
    
    # Update work with scores
    if "antiplagiarism" in analysis_results:
        work.ai_plagiarism_score = analysis_results["antiplagiarism"].get("score", 0)
    if "structure" in analysis_results:
        work.ai_structure_score = analysis_results["structure"].get("score", 0)
    if "formatting" in analysis_results:
        work.ai_formatting_score = analysis_results["formatting"].get("score", 0)
    
    work.ai_analysis_json = analysis_results
    work.analysis_started_at = datetime.utcnow()
    work.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "success": True,
        "work_id": work_id,
        "analysis": analysis_results,
        "tokens_used": total_tokens,
        "estimated_cost_usd": round(total_cost, 6),
    }


# ============== MESSAGE TEMPLATES ==============

@router.get("/templates")
async def list_templates(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Список шаблонов сообщений"""
    query = select(MessageTemplate).where(MessageTemplate.is_active == True)
    
    if category:
        query = query.where(MessageTemplate.category == category)
    
    query = query.order_by(MessageTemplate.name)
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "category": t.category,
            "trigger_event": t.trigger_event,
            "subject_template": t.subject_template,
            "body_template": t.body_template[:200] + "..." if len(t.body_template) > 200 else t.body_template,
            "variables": t.variables,
            "is_active": t.is_active,
        }
        for t in templates
    ]


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Получить шаблон по ID"""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == UUID(template_id))
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": str(template.id),
        "name": template.name,
        "category": template.category,
        "trigger_event": template.trigger_event,
        "subject_template": template.subject_template,
        "body_template": template.body_template,
        "variables": template.variables,
        "is_active": template.is_active,
    }


@router.post("/templates")
async def create_template(
    template_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Создать шаблон сообщения"""
    new_template = MessageTemplate(
        id=uuid4(),
        name=template_data.get("name"),
        category=template_data.get("category", "auto_response"),
        trigger_event=template_data.get("trigger_event"),
        subject_template=template_data.get("subject_template"),
        body_template=template_data.get("body_template"),
        variables=template_data.get("variables", []),
        is_active=template_data.get("is_active", True),
        created_by=UUID(user.get("user_id")) if user.get("user_id") else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(new_template)
    await db.commit()
    
    return {
        "id": str(new_template.id),
        "name": new_template.name,
        "category": new_template.category,
    }


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    update_data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Обновить шаблон"""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == UUID(template_id))
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    for field in ["name", "category", "trigger_event", "subject_template", 
                  "body_template", "variables", "is_active"]:
        if field in update_data:
            setattr(template, field, update_data[field])
    
    template.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True, "message": "Template updated"}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Удалить шаблон (soft delete - set inactive)"""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == UUID(template_id))
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template.is_active = False
    template.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True, "message": "Template deleted"}


# ============== AUTO-MESSAGING ==============

@router.post("/send-template")
async def send_template_message(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Отправить сообщение по шаблону (триггер или ручная отправка)"""
    template_id = data.get("template_id")
    work_id = data.get("work_id")
    recipient_id = data.get("recipient_id")  # student_id
    custom_vars = data.get("variables", {})
    
    # Get template
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == UUID(template_id))
    )
    template = result.scalar_one_or_none()
    
    if not template or not template.is_active:
        raise HTTPException(status_code=404, detail="Template not found or inactive")
    
    # Get recipient
    result = await db.execute(select(User).where(User.id == UUID(recipient_id)))
    recipient = result.scalar_one_or_none()
    
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Get work data if provided
    work_data = {}
    if work_id:
        result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
        work = result.scalar_one_or_none()
        if work:
            work_data = {
                "work_title": work.title,
                "work_id": str(work.id),
                "ai_plagiarism_score": work.ai_plagiarism_score,
                "ai_structure_score": work.ai_structure_score,
                "ai_formatting_score": work.ai_formatting_score,
                "teacher_comment": work.teacher_comment,
                "status": work.status,
            }
    
    # Prepare variables
    variables = {
        "student_name": recipient.full_name or recipient.username,
        **work_data,
        **custom_vars,
    }
    
    # Render template
    subject = template.subject_template
    body = template.body_template
    
    for key, value in variables.items():
        placeholder = "{" + key + "}"
        subject = subject.replace(placeholder, str(value)) if subject else subject
        body = body.replace(placeholder, str(value))
    
    # Create communication record
    communication = Communication(
        id=uuid4(),
        work_id=UUID(work_id) if work_id else None,
        sender_id=UUID(user.get("user_id")) if user.get("user_id") else None,
        recipient_id=recipient.id,
        message=body,
        message_type="template",
        is_read=False,
        created_at=datetime.utcnow(),
    )
    db.add(communication)
    await db.commit()
    
    # TODO: Send actual Telegram message via bot API
    # This would require integration with the bot service
    
    return {
        "success": True,
        "message": "Template message queued",
        "communication_id": str(communication.id),
        "rendered_body": body[:500],
    }


@router.post("/bulk-send")
async def bulk_send_message(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Массовая рассылка сообщений"""
    template_id = data.get("template_id")
    recipient_type = data.get("recipient_type")  # all, by_status, by_work_type
    filter_criteria = data.get("filter", {})
    custom_vars = data.get("variables", {})
    
    # Build recipient query
    from sqlalchemy import select
    query = select(User).where(User.role == "student")
    
    if recipient_type == "by_status":
        # Get students with works in specific status
        status = filter_criteria.get("status")
        # This would require a join query
        pass
    
    result = await db.execute(query)
    recipients = result.scalars().all()
    
    sent_count = 0
    for recipient in recipients:
        try:
            # Send to each recipient
            # TODO: Implement actual sending
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {recipient.id}: {e}")
    
    return {
        "success": True,
        "recipients_count": len(recipients),
        "sent_count": sent_count,
    }

@router.post("/{work_id}/generate-student-response")
async def generate_student_response(
    work_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Сгенерировать персонализированный ответ для студента на основе AI анализа"""
    # Get work
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Check if AI analysis exists
    if not work.ai_analysis_json:
        raise HTTPException(status_code=400, detail="AI analysis not completed yet")
    
    # Get active AI provider
    result = await db.execute(select(AIProvider).where(AIProvider.is_active == True).limit(1))
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(status_code=500, detail="No active AI provider configured")
    
    # Get student info
    result = await db.execute(select(User).where(User.id == work.student_id))
    student = result.scalar_one_or_none()
    
    student_name = student.full_name if student else "Студент"
    
    # Build prompt for student response
    ai_data = work.ai_analysis_json
    
    prompt = f"""Ты — преподаватель, который проверяет научную работу студента. 
Напиши персонализированный отзыв для студента {student_name}.

Результаты AI анализа работы \"{work.title}\":

Оценки:
- Оригинальность текста: {work.ai_plagiarism_score or 'N/A'}%
- Структура работы: {work.ai_structure_score or 'N/A'}/10  
- Оформление (ГОСТ): {work.ai_formatting_score or 'N/A'}/10

Детальный анализ:
{json.dumps(ai_data, ensure_ascii=False, indent=2)}

Напиши отзыв в следующей структуре:

1. Приветствие и общая оценка работы (1-2 предложения)
2. Сильные стороны работы (2-3 предложения с конкретикой)
3. Слабые стороны работы (2-3 предложения с конкретикой)
4. Рекомендации для доработки (3-4 конкретных пункта)
5. Заключение с пожеланием (1-2 предложения)

Тон: конструктивный, уважительный, мотивирующий. Не используй общих фраз типа \"хорошая работа\" без объяснения почему.

Верни ответ в формате JSON:
{{
    "greeting": "...",
    "strengths": "...", 
    "weaknesses": "...",
    "recommendations": "...",
    "conclusion": "...",
    "full_text": "полный текст ответа для отправки студенту"
}}"""
    
    try:
        # Generate response using OpenRouter
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{provider.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {provider.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://digitatal-tutor.example.com",
                    "X-Title": "DigitalTutor"
                },
                json={
                    "model": provider.default_model or "openai/gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "Ты — опытный преподаватель, который даёт конструктивную обратную связь по научным работам."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=60.0
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"AI generation failed: {response.status_code}")
            
            data = response.json()
            ai_response = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            
            # Parse JSON from AI response
            try:
                # Try to extract JSON if wrapped in markdown
                import re
                json_match = re.search(r'```json\s*(.*?)```', ai_response, re.DOTALL)
                if json_match:
                    ai_response = json_match.group(1)
                
                response_data = json.loads(ai_response)
            except json.JSONDecodeError:
                # If not valid JSON, wrap it
                response_data = {
                    "greeting": "",
                    "strengths": "",
                    "weaknesses": "", 
                    "recommendations": "",
                    "conclusion": "",
                    "full_text": ai_response
                }
            
            # Store in work
            work.ai_student_response = response_data
            work.ai_student_response_status = "pending_review"  # pending_review, approved, sent
            await db.commit()
            
            return {
                "success": True,
                "work_id": work_id,
                "response": response_data,
                "tokens_used": tokens_used,
                "status": "pending_review"
            }
            
    except Exception as e:
        logger.error(f"Failed to generate student response: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/{work_id}/send-student-response")
async def send_student_response(
    work_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(verify_token)
):
    """Отправить сгенерированный ответ студенту (после редактирования/одобрения)"""
    result = await db.execute(select(StudentWork).where(StudentWork.id == UUID(work_id)))
    work = result.scalar_one_or_none()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Get student
    result = await db.execute(select(User).where(User.id == work.student_id))
    student = result.scalar_one_or_none()
    
    if not student or not student.telegram_id:
        raise HTTPException(status_code=400, detail="Student has no Telegram ID")
    
    # Get response text (edited or original)
    response_text = data.get("response_text") or work.ai_student_response.get("full_text", "")
    
    if not response_text:
        raise HTTPException(status_code=400, detail="No response text provided")
    
    # Store final response
    work.ai_student_response["full_text"] = response_text
    work.ai_student_response_status = "sent"
    work.teacher_comment = response_text  # Also store as teacher comment
    work.status = "graded"
    await db.commit()
    
    # Return data for bot to send
    return {
        "success": True,
        "work_id": work_id,
        "student_telegram_id": student.telegram_id,
        "response_text": response_text,
        "status": "sent"
    }


