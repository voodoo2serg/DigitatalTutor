"""
DigitalTutor Bot - AI Service (Multi-Provider)
Поддержка: Cerebras, OpenRouter, Ollama, HuggingFace
"""
import logging
import httpx
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AIService:
    """Мультипровайдерный AI-сервис"""

    def __init__(self):
        self.providers = {}

    def register_provider(self, name: str, api_key: str, base_url: str, default_model: str, is_active: bool = True):
        """Register an AI provider"""
        self.providers[name] = {
            "api_key": api_key,
            "base_url": base_url,
            "default_model": default_model,
            "is_active": is_active,
        }

    def get_active_providers(self) -> List[str]:
        """Get list of active provider names"""
        return [name for name, config in self.providers.items() if config.get("is_active") and config.get("api_key")]

    def get_provider_info(self) -> Dict[str, Any]:
        """Get info about all providers (for admin display)"""
        result = {}
        for name, config in self.providers.items():
            result[name] = {
                "is_active": config.get("is_active", False),
                "has_api_key": bool(config.get("api_key")),
                "base_url": config.get("base_url", ""),
                "default_model": config.get("default_model", ""),
            }
        return result

    async def analyze_text(self, text: str, prompt: str, skill_name: str, preferred_provider: Optional[str] = None) -> Dict[str, Any]:
        """Analyze text using the best available provider with fallback"""

        # Try preferred provider first
        if preferred_provider and preferred_provider in self.providers:
            result = await self._call_provider(preferred_provider, text, prompt, skill_name)
            if result:
                return result

        # Fallback through active providers in order: cerebras -> openrouter -> ollama -> huggingface
        priority_order = ["cerebras", "openrouter", "ollama", "huggingface"]
        for provider_name in priority_order:
            if provider_name in self.providers and provider_name != preferred_provider:
                result = await self._call_provider(provider_name, text, prompt, skill_name)
                if result:
                    return result

        return {"error": "No active AI provider available", "score": 0}

    async def _call_provider(self, provider_name: str, text: str, prompt: str, skill_name: str) -> Optional[Dict[str, Any]]:
        """Call a specific provider"""
        config = self.providers[provider_name]

        if not config.get("is_active") or not config.get("api_key"):
            return None

        try:
            if provider_name == "cerebras":
                return await self._call_cerebras(config, text, prompt, skill_name)
            elif provider_name == "openrouter":
                return await self._call_openrouter(config, text, prompt, skill_name)
            elif provider_name == "ollama":
                return await self._call_ollama(config, text, prompt, skill_name)
            elif provider_name == "huggingface":
                return await self._call_huggingface(config, text, prompt, skill_name)
        except Exception as e:
            logger.error(f"Provider {provider_name} failed: {e}")
            return None

    async def _call_cerebras(self, config: dict, text: str, prompt: str, skill_name: str) -> Dict[str, Any]:
        """Cerebras API - fastest"""
        import time
        start_time = time.time()

        full_prompt = (
            f"{prompt}\n\nАнализируемый текст:\n---\n{text[:8000]}\n---\n\n"
            'Ответь в формате JSON:\n{"score": число от 0 до 100, '
            '"assessment": "краткая оценка", '
            '"findings": ["список", "проблем"], '
            '"recommendations": ["список", "рекомендаций"]}'
        )

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": config.get("default_model", "llama-4-scout-17b-16e-instruct"),
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0
            )

            processing_time = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(f"Cerebras error: {response.status_code} - {response.text}")
                return None

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = self._parse_json_response(content)

            return {
                "result": result,
                "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                "processing_time_ms": processing_time,
                "provider": "cerebras",
                "model": config.get("default_model"),
            }

    async def _call_openrouter(self, config: dict, text: str, prompt: str, skill_name: str) -> Dict[str, Any]:
        """OpenRouter API - fallback"""
        import time
        start_time = time.time()

        full_prompt = (
            f"{prompt}\n\nАнализируемый текст:\n---\n{text[:8000]}\n---\n\n"
            'Ответь в формате JSON:\n{"score": число от 0 до 100, '
            '"assessment": "краткая оценка", '
            '"findings": ["список", "проблем"], '
            '"recommendations": ["список", "рекомендаций"]}'
        )

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://digitatal-tutor.example.com",
            "X-Title": "DigitalTutor"
        }

        payload = {
            "model": config.get("default_model", "openai/gpt-4o-mini"),
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120.0
            )

            processing_time = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(f"OpenRouter error: {response.status_code} - {response.text}")
                return None

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = self._parse_json_response(content)

            return {
                "result": result,
                "tokens_used": data.get("usage", {}).get("total_tokens", 0),
                "processing_time_ms": processing_time,
                "provider": "openrouter",
                "model": config.get("default_model"),
            }

    async def _call_ollama(self, config: dict, text: str, prompt: str, skill_name: str) -> Dict[str, Any]:
        """Ollama - local inference"""
        import time
        start_time = time.time()

        full_prompt = (
            f"{prompt}\n\nАнализируемый текст:\n---\n{text[:6000]}\n---\n\n"
            'Ответь в формате JSON:\n{"score": число от 0 до 100, '
            '"assessment": "краткая оценка", '
            '"findings": ["список", "проблем"], '
            '"recommendations": ["список", "рекомендаций"]}'
        )

        payload = {
            "model": config.get("default_model", "gemma3:4b"),
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0.3},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['base_url']}/api/generate",
                json=payload,
                timeout=300.0  # Ollama can be slow
            )

            processing_time = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(f"Ollama error: {response.status_code}")
                return None

            data = response.json()
            content = data.get("response", "")
            result = self._parse_json_response(content)

            return {
                "result": result,
                "tokens_used": data.get("eval_count", 0),
                "processing_time_ms": processing_time,
                "provider": "ollama",
                "model": config.get("default_model"),
            }

    async def _call_huggingface(self, config: dict, text: str, prompt: str, skill_name: str) -> Dict[str, Any]:
        """HuggingFace Inference API"""
        import time
        start_time = time.time()

        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }

        full_prompt = f"{prompt}\n\n{text[:4000]}"

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 1000,
                "temperature": 0.3,
                "return_full_text": False,
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config['base_url']}",
                headers=headers,
                json=payload,
                timeout=120.0
            )

            processing_time = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(f"HuggingFace error: {response.status_code}")
                return None

            data = response.json()
            content = data[0]["generated_text"] if isinstance(data, list) else str(data)
            result = self._parse_json_response(content)

            return {
                "result": result,
                "tokens_used": 0,
                "processing_time_ms": processing_time,
                "provider": "huggingface",
                "model": config.get("default_model", ""),
            }

    def _parse_json_response(self, content: str) -> Dict:
        """Parse JSON from AI response, handling markdown wrapping"""
        import re
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try extracting from markdown code block
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Return raw text as assessment
            return {
                "score": 50,
                "assessment": content[:1000],
                "findings": [],
                "recommendations": [],
            }

    async def generate_review(self, text: str, work_title: str, student_name: str, analysis_data: Dict, preferred_provider: Optional[str] = None) -> str:
        """Generate a comprehensive review for a student's work"""

        prompt = (
            f"Ты — преподаватель, который проверяет научную работу студента {student_name}.\n"
            f'Напиши подробную рецензию на работу "{work_title}".\n\n'
            f"Результаты автоматического анализа:\n"
            f"- Оригинальность: {analysis_data.get('antiplagiarism', {}).get('score', 'N/A')}%\n"
            f"- Структура: {analysis_data.get('structure', {}).get('score', 'N/A')}/100\n"
            f"- Оформление: {analysis_data.get('formatting', {}).get('score', 'N/A')}/100\n\n"
            "Напиши рецензию:\n"
            "1. Общая оценка (1-2 предложения)\n"
            "2. Сильные стороны (2-3 предложения)\n"
            "3. Слабые стороны (2-3 предложения)\n"
            "4. Рекомендации (3-4 пункта)\n"
            "5. Заключение\n\n"
            "Тон: конструктивный, уважительный, мотивирующий."
        )

        full_prompt = f"{prompt}\n\nТекст работы (фрагмент):\n---\n{text[:6000]}\n---"

        # Try to generate using any available provider
        if preferred_provider and preferred_provider in self.providers:
            config = self.providers[preferred_provider]
            if config.get("is_active") and config.get("api_key"):
                result = await self._generate_simple(preferred_provider, config, full_prompt)
                if result:
                    return result

        for name in ["cerebras", "openrouter", "ollama", "huggingface"]:
            if name in self.providers:
                config = self.providers[name]
                if config.get("is_active") and config.get("api_key"):
                    result = await self._generate_simple(name, config, full_prompt)
                    if result:
                        return result

        return "Не удалось сгенерировать рецензию. Нет доступных AI-провайдеров."

    async def _generate_simple(self, provider_name: str, config: dict, prompt: str) -> Optional[str]:
        """Simple text generation (no JSON parsing)"""
        try:
            if provider_name == "ollama":
                payload = {
                    "model": config.get("default_model", "gemma3:4b"),
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7},
                }
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{config['base_url']}/api/generate",
                        json=payload,
                        timeout=300.0
                    )
                    if response.status_code == 200:
                        return response.json().get("response", "")
            else:
                base_url = config["base_url"]
                headers = {
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                }

                if provider_name == "cerebras":
                    headers.pop("Content-Type", None)  # Cerebras may not need it explicitly
                elif provider_name == "openrouter":
                    headers["HTTP-Referer"] = "https://digitatal-tutor.example.com"
                    headers["X-Title"] = "DigitalTutor"

                payload = {
                    "model": config.get("default_model"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=120.0
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Simple generation failed for {provider_name}: {e}")
        return None


# Global AI service instance
ai_service = AIService()


def init_ai_service():
    """Initialize AI service with providers from environment"""
    import os

    # Cerebras (primary - fastest)
    cerebras_key = os.getenv("CEREBRAS_API_KEY", "")
    if cerebras_key:
        ai_service.register_provider(
            name="cerebras",
            api_key=cerebras_key,
            base_url="https://api.cerebras.ai",
            default_model=os.getenv("CEREBRAS_MODEL", "llama-4-scout-17b-16e-instruct"),
            is_active=True,
        )

    # OpenRouter (fallback)
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key:
        ai_service.register_provider(
            name="openrouter",
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api",
            default_model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            is_active=True,
        )

    # Ollama (local)
    ollama_url = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    # Ollama doesn't need an API key, use placeholder
    ai_service.register_provider(
        name="ollama",
        api_key="local",  # Placeholder for local inference
        base_url=ollama_url,
        default_model=ollama_model,
        is_active=True,
    )

    # HuggingFace
    hf_key = os.getenv("HUGGINGFACE_API_KEY", "")
    if hf_key:
        ai_service.register_provider(
            name="huggingface",
            api_key=hf_key,
            base_url=os.getenv(
                "HUGGINGFACE_URL",
                "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
            ),
            default_model="meta-llama/Meta-Llama-3-8B-Instruct",
            is_active=True,
        )

    active = ai_service.get_active_providers()
    logger.info(f"AI Service initialized. Active providers: {active}")
