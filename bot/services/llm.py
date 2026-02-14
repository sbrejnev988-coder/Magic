"""
РЎРµСЂРІРёСЃ РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ LLM (OpenAI/Perplexity/Featherless)
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx
from bot.config import Settings

log = logging.getLogger(__name__)


class LLMService:
    """РЎРµСЂРІРёСЃ РґР»СЏ РіРµРЅРµСЂР°С†РёРё С‚РµРєСЃС‚РѕРІ С‡РµСЂРµР· LLM API"""
    
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
        """Р—Р°РіСЂСѓР·РєР° СЃРёСЃС‚РµРјРЅРѕРіРѕ РїСЂРѕРјРїС‚Р° РёР· С„Р°Р№Р»Р°."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "system.md"
        try:
            if prompt_path.exists():
                return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            log.error(f"РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ СЃРёСЃС‚РµРјРЅС‹Р№ РїСЂРѕРјРїС‚: {e}")
        
        # РџСЂРѕРјРїС‚ РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ
        return "РўС‹ вЂ” СЌР·РѕС‚РµСЂРёС‡РµСЃРєРёР№ РїРѕРјРѕС‰РЅРёРє MysticBot. РћС‚РІРµС‡Р°Р№ РЅР° СЂСѓСЃСЃРєРѕРј СЏР·С‹РєРµ."
        
    async def generate_interpretation(self, prompt: str, context: str = "") -> Optional[str]:
        """
        Р“РµРЅРµСЂР°С†РёСЏ РёРЅС‚РµСЂРїСЂРµС‚Р°С†РёРё С‡РµСЂРµР· LLM СЃ fallback-С†РµРїРѕС‡РєРѕР№:
        Featherless в†’ Perplexity в†’ OpenAI
        
        Args:
            prompt: Р—Р°РїСЂРѕСЃ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
            context: РљРѕРЅС‚РµРєСЃС‚ (РЅР°РїСЂРёРјРµСЂ, С‚РёРї СЂР°СЃРєР»Р°РґР°)
            
        Returns:
            РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ С‚РµРєСЃС‚ РёР»Рё None РїСЂРё РѕС€РёР±РєРµ
        """
        # РџСЂРѕРІРµСЂРєР° РґРѕСЃС‚СѓРїРЅРѕСЃС‚Рё API РєР»СЋС‡РµР№
        if not self.settings.is_llm_configured:
            log.warning("LLM РЅРµ РЅР°СЃС‚СЂРѕРµРЅ: РѕС‚СЃСѓС‚СЃС‚РІСѓСЋС‚ API РєР»СЋС‡Рё")
            return None
        
        # РРЅРёС†РёР°Р»РёР·РёСЂСѓРµРј РєР»РёРµРЅС‚ РµСЃР»Рё РЅРµ СЃРѕР·РґР°РЅ
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        
        # Р¤РѕСЂРјРёСЂРѕРІР°РЅРёРµ Р·Р°РїСЂРѕСЃР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ СЃ РєРѕРЅС‚РµРєСЃС‚РѕРј
        user_message = f"{context}\n\n{prompt}" if context else prompt
        
        # Р¦РµРїРѕС‡РєР° fallback: Featherless в†’ Perplexity в†’ OpenAI
        if self.settings.FEATHERLESS_API_KEY:
            log.info("РџСЂРѕР±СѓРµРј Featherless API (РїСЂРёРѕСЂРёС‚РµС‚ 1)")
            result = await self._call_featherless(user_message)
            if result is not None:
                return result
            log.warning("Featherless API РІРµСЂРЅСѓР» None, РїСЂРѕР±СѓРµРј Perplexity")
        
        if self.settings.PERPLEXITY_API_KEY:
            log.info("РџСЂРѕР±СѓРµРј Perplexity API (РїСЂРёРѕСЂРёС‚РµС‚ 2)")
            result = await self._call_perplexity(user_message)
            if result is not None:
                return result
            log.warning("Perplexity API РІРµСЂРЅСѓР» None, РїСЂРѕР±СѓРµРј OpenAI")
        
        if self.settings.OPENAI_API_KEY:
            log.info("РџСЂРѕР±СѓРµРј OpenAI API (РїСЂРёРѕСЂРёС‚РµС‚ 3)")
            result = await self._call_openai(user_message)
            if result is not None:
                return result
        
        log.error("Р’СЃРµ LLM РїСЂРѕРІР°Р№РґРµСЂС‹ РІРµСЂРЅСѓР»Рё РѕС€РёР±РєСѓ")
        return None
    
    async def _call_perplexity(self, user_message: str) -> Optional[str]:
        """Р’С‹Р·РѕРІ Perplexity API"""
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
                        "content": self.system_prompt  # вњ… Р‘Р•Р— [:500]
                    },
                    {
                        "role": "user",
                        "content": user_message  # вњ… Р‘Р•Р— [:1000]
                    }
                ],
                "max_tokens": 1000,  # вњ… РЈРІРµР»РёС‡РµРЅРѕ СЃ 500
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
        """Р’С‹Р·РѕРІ OpenAI API"""
        log.info(f"Calling OpenAI API with message length: {len(user_message)}")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.settings.OPENAI_MODEL,  # вњ… РР· РєРѕРЅС„РёРіР°
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt  # вњ… Р‘Р•Р— [:500]
                    },
                    {
                        "role": "user",
                        "content": user_message  # вњ… Р‘Р•Р— [:1000]
                    }
                ],
                "max_tokens": 1000,  # вњ… РЈРІРµР»РёС‡РµРЅРѕ СЃ 500
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
    
    async def _call_featherless(self, user_message: str) -> Optional[str]:
        """Р’С‹Р·РѕРІ Featherless API СЃ РїРѕРґРґРµСЂР¶РєРѕР№ С…РѕР»РѕРґРЅРѕРіРѕ СЃС‚Р°СЂС‚Р° Рё retry"""
        log.info(f"Calling Featherless API with message length: {len(user_message)}")
        
        # РџСЂРѕРІРµСЂРєР° РЅР°Р»РёС‡РёСЏ base_url (РїСЂРёРѕСЂРёС‚РµС‚) РёР»Рё endpoint
        if self.settings.FEATHERLESS_BASE_URL:
            base_url = self.settings.FEATHERLESS_BASE_URL.rstrip('/')
            endpoint = f"{base_url}/chat/completions"
        elif self.settings.FEATHERLESS_ENDPOINT:
            # Р”Р»СЏ РѕР±СЂР°С‚РЅРѕР№ СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚Рё: РµСЃР»Рё endpoint РїРѕР»РЅС‹Р№, РёСЃРїРѕР»СЊР·СѓРµРј РµРіРѕ
            if '/chat/completions' in self.settings.FEATHERLESS_ENDPOINT:
                endpoint = self.settings.FEATHERLESS_ENDPOINT
                base_url = self.settings.FEATHERLESS_ENDPOINT.replace('/chat/completions', '')
            else:
                endpoint = f"{self.settings.FEATHERLESS_ENDPOINT.rstrip('/')}/chat/completions"
                base_url = self.settings.FEATHERLESS_ENDPOINT
        else:
            log.error("Р”Р»СЏ Featherless API С‚СЂРµР±СѓРµС‚СЃСЏ FEATHERLESS_BASE_URL РёР»Рё FEATHERLESS_ENDPOINT РІ РєРѕРЅС„РёРіСѓСЂР°С†РёРё")
            return None
        
        log.info(f"РСЃРїРѕР»СЊР·СѓРµРј Featherless endpoint: {endpoint}, РјРѕРґРµР»СЊ: {self.settings.FEATHERLESS_MODEL}")
        
        # РўР°Р№РјР°СѓС‚С‹ РёР· РєРѕРЅС„РёРіР° (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 180 СЃРµРє РґР»СЏ С…РѕР»РѕРґРЅРѕРіРѕ СЃС‚Р°СЂС‚Р°)
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self.settings.FEATHERLESS_TIMEOUT),
            write=10.0,
            pool=10.0
        )
        
        # РСЃРїРѕР»СЊР·СѓРµРј РѕС‚РґРµР»СЊРЅС‹Р№ РєР»РёРµРЅС‚ СЃ СѓРІРµР»РёС‡РµРЅРЅС‹РјРё С‚Р°Р№РјР°СѓС‚Р°РјРё
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {
                "Authorization": f"Bearer {self.settings.FEATHERLESS_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.settings.FEATHERLESS_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "max_tokens": self.settings.FEATHERLESS_MAX_TOKENS,  # Р—Р°С‰РёС‚Р° РѕС‚ Р°Р±СѓР·Р°, РЅР°СЃС‚СЂР°РёРІР°РµС‚СЃСЏ РІ .env
                "temperature": 0.7
            }
            
            # Retry-Р»РѕРіРёРєР° РґР»СЏ 503 (РјРѕРґРµР»СЊ Р·Р°РіСЂСѓР¶Р°РµС‚СЃСЏ) Рё СЃРµС‚РµРІС‹С… РѕС€РёР±РѕРє
            max_attempts = self.settings.FEATHERLESS_MAX_RETRIES
            for attempt in range(max_attempts):
                try:
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        json=data
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result["choices"][0]["message"]["content"]
                        log.info(f"Featherless API success, response length: {len(content)}")
                        return content
                    elif response.status_code == 503:
                        # РњРѕРґРµР»СЊ Р·Р°РіСЂСѓР¶Р°РµС‚СЃСЏ, Р¶РґС‘Рј Рё РїРѕРІС‚РѕСЂСЏРµРј
                        wait_time = 30 * (attempt + 1)  # 30, 60, 90 СЃРµРєСѓРЅРґ
                        log.warning(f"Featherless API 503 (РјРѕРґРµР»СЊ Р·Р°РіСЂСѓР¶Р°РµС‚СЃСЏ), attempt {attempt+1}/{max_attempts}, waiting {wait_time} sec")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        log.error(f"Featherless API error: {response.status_code}")
                        log.error(f"Response body: {response.text[:500]}")
                        return None
                        
                except httpx.TimeoutException:
                    log.error(f"Featherless API timeout attempt {attempt+1}/{max_attempts}")
                    if attempt == max_attempts - 1:
                        log.error("Featherless API timeout after all retries")
                        return None
                    await asyncio.sleep(10)
                    continue
                except httpx.RequestError as e:
                    log.error(f"Featherless API request error: {e}")
                    if attempt == max_attempts - 1:
                        return None
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    log.error(f"Featherless API exception: {e}", exc_info=True)
                    return None
            
            # Р•СЃР»Рё РІСЃРµ РїРѕРїС‹С‚РєРё РёСЃС‡РµСЂРїР°РЅС‹
            log.error(f"Featherless API failed after {max_attempts} attempts")
            return None
    
    async def close(self):
        """Р—Р°РєСЂС‹С‚РёРµ РєР»РёРµРЅС‚Р°"""
        if self.client:
            await self.client.aclose()
            self.client = None


# Р“Р»РѕР±Р°Р»СЊРЅС‹Р№ СЌРєР·РµРјРїР»СЏСЂ СЃРµСЂРІРёСЃР°
_llm_service: Optional[LLMService] = None


def get_llm_service(settings: Settings) -> LLMService:
    """РџРѕР»СѓС‡РёС‚СЊ РёР»Рё СЃРѕР·РґР°С‚СЊ СЌРєР·РµРјРїР»СЏСЂ LLMService"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(settings)
    return _llm_service


async def shutdown_llm_service():
    """Р—Р°РІРµСЂС€РµРЅРёРµ СЂР°Р±РѕС‚С‹ СЃРµСЂРІРёСЃР°"""
    global _llm_service
    if _llm_service:
        await _llm_service.close()
        _llm_service = None