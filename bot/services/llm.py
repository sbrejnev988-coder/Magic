"""
Сервис для работы с LLM (OpenAI/Perplexity)
"""

import logging
from pathlib import Path
from typing import Optional

import httpx
from bot.config import Settings

log = logging.getLogger(__name__)


class LLMService:
    """Сервис для генерации текстов через LLM API"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None
        self.system_prompt = self._load_system_prompt()
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    def _load_system_prompt(self) -> str:
        """Загрузка системного промпта из файла."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "system.md"
        try:
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            log.error(f"Не удалось загрузить системный промпт: {e}")
        
        # Промпт по умолчанию
        return "Ты — эзотерический помощник MysticBot. Отвечай на русском языке."
        
    async def generate_interpretation(self, prompt: str, context: str = "") -> Optional[str]:
        """
        Генерация интерпретации через LLM
        
        Args:
            prompt: Запрос пользователя
            context: Контекст (например, тип расклада)
            
        Returns:
            Сгенерированный текст или None при ошибке
        """
        # Проверка доступности API ключей
        if not self.settings.is_llm_configured:
            log.warning("LLM не настроен: отсутствуют API ключи")
            return None
        
        # Инициализируем клиент если не создан
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        
        # Формирование запроса пользователя с контекстом
        user_message = f"{context}\n\n{prompt}" if context else prompt
        
        # Выбор провайдера
        if self.settings.PERPLEXITY_API_KEY:
            return await self._call_perplexity(user_message)
        elif self.settings.OPENAI_API_KEY:
            return await self._call_openai(user_message)
        else:
            return None
    
    async def _call_perplexity(self, user_message: str) -> Optional[str]:
        """Вызов Perplexity API"""
        log.info(f"Calling Perplexity API with message length: {len(user_message)}")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.settings.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.settings.PERPLEXITY_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt  # ✅ БЕЗ [:500]
                    },
                    {
                        "role": "user",
                        "content": user_message  # ✅ БЕЗ [:1000]
                    }
                ],
                "max_tokens": 1000,  # ✅ Увеличено с 500
                "temperature": 0.7
            }
            
            response = await self.client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                log.info(f"Perplexity API success, response length: {len(content)}")
                return content
            else:
                log.error(f"Perplexity API error: {response.status_code}")
                log.error(f"Response body: {response.text[:500]}")
                return None
                
        except httpx.TimeoutException:
            log.error("Perplexity API timeout after 30 seconds")
            return None
        except httpx.RequestError as e:
            log.error(f"Perplexity API request error: {e}")
            return None
        except Exception as e:
            log.error(f"Perplexity API exception: {e}", exc_info=True)
            return None
    
    async def _call_openai(self, user_message: str) -> Optional[str]:
        """Вызов OpenAI API"""
        log.info(f"Calling OpenAI API with message length: {len(user_message)}")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.settings.OPENAI_MODEL,  # ✅ Из конфига
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt  # ✅ БЕЗ [:500]
                    },
                    {
                        "role": "user",
                        "content": user_message  # ✅ БЕЗ [:1000]
                    }
                ],
                "max_tokens": 1000,  # ✅ Увеличено с 500
                "temperature": 0.7
            }
            
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                log.info(f"OpenAI API success, response length: {len(content)}")
                return content
            else:
                log.error(f"OpenAI API error: {response.status_code}")
                log.error(f"Response body: {response.text[:500]}")
                return None
                
        except httpx.TimeoutException:
            log.error("OpenAI API timeout after 30 seconds")
            return None
        except httpx.RequestError as e:
            log.error(f"OpenAI API request error: {e}")
            return None
        except Exception as e:
            log.error(f"OpenAI API exception: {e}", exc_info=True)
            return None
    
    async def close(self):
        """Закрытие клиента"""
        if self.client:
            await self.client.aclose()
            self.client = None


# Глобальный экземпляр сервиса
_llm_service: Optional[LLMService] = None


def get_llm_service(settings: Settings) -> LLMService:
    """Получить или создать экземпляр LLMService"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(settings)
    return _llm_service


async def shutdown_llm_service():
    """Завершение работы сервиса"""
    global _llm_service
    if _llm_service:
        await _llm_service.close()
        _llm_service = None