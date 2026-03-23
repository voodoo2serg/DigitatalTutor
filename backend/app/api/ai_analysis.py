from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.models.models import StudentWork, File

router = APIRouter()

@router.post("/analyze/{work_id}")
async def analyze_work(work_id: str, db: AsyncSession = Depends(get_db)):
    # Get work
    result = await db.execute(select(StudentWork).where(StudentWork.id == work_id))
    work = result.scalar_one_or_none()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # Get files with extracted text
    result = await db.execute(
        select(File).where(
            (File.work_id == work_id) & 
            (File.ai_extracted_text != None)
        )
    )
    files = result.scalars().all()
    
    if not files:
        return {"error": "No files with extracted text found"}
    
    # Combine text from all files
    full_text = "\n\n".join([f.ai_extracted_text for f in files if f.ai_extracted_text])
    
    # Analyze with Ollama
    analysis_result = await analyze_with_ollama(full_text)
    
    # Update work with analysis
    work.ai_analysis_json = analysis_result
    work.ai_plagiarism_score = analysis_result.get('plagiarism_score')
    work.ai_structure_score = analysis_result.get('structure_score')
    work.ai_formatting_score = analysis_result.get('formatting_score')
    
    await db.commit()
    
    return {
        "work_id": work_id,
        "analysis": analysis_result
    }

async def analyze_with_ollama(text: str) -> dict:
    """Analyze text using local Ollama instance."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": f"""Проанализируй следующий текст научной работы и верни результат в JSON формате:

Текст: {text[:5000]}...

Проанализируй:
1. Уникальность/плагиат (plagiarism_score от 0 до 100)
2. Структура работы (structure_score от 0 до 100)
3. Оформление (formatting_score от 0 до 100)
4. Ключевые выводы
5. Риски и проблемы

Ответь ТОЛЬКО в формате JSON без пояснений:
{{
    "plagiarism_score": 85,
    "structure_score": 70,
    "formatting_score": 90,
    "key_findings": "...",
    "risks": "..."
}}""",
                    "stream": False
                },
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                # Parse JSON from response
                try:
                    import json
                    response_text = result.get('response', '{}')
                    return json.loads(response_text)
                except:
                    return {
                        "plagiarism_score": None,
                        "structure_score": None,
                        "formatting_score": None,
                        "raw_response": result.get('response')
                    }
            else:
                return {"error": f"Ollama error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

@router.get("/skills")
async def list_ai_skills():
    return {
        "skills": [
            {"name": "antiplagiarism", "description": "Проверка на плагиат и AI-генерацию"},
            {"name": "structure", "description": "Анализ структуры научной работы"},
            {"name": "formatting", "description": "Проверка оформления по ГОСТ"}
        ]
    }
