"""
MysticBot — LLM Service
Единый сервис для работы с LLM-провайдерами.
Приоритет: Featherless → Perplexity → OpenAI.
Поддержка: retry при 503, таймауты, graceful fallback.
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from bot.config import settings, FeatherlessConfig, PerplexityConfig, OpenAIConfig

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Базовая ошибка LLM-сервиса."""
    pass


class AllProvidersFailedError(LLMError):
    """Все провайдеры недоступны."""
    pass


class LLMProvider:
    """
    Обёртка для одного LLM-провайдера (OpenAI-совместимый API).
    Поддерживает retry при 503 и настраиваемый таймаут.
    """

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 30.0,
    ):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Единый httpx-клиент с настроенным таймаутом
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Ленивая инициализация httpx-клиента."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=float(self.timeout),
                    write=10.0,
                    pool=10.0,
                ),
            )
        return self._client

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> dict:
        """
        Отправка запроса к /chat/completions с retry-логикой.

        Args:
            messages: Список сообщений [{role, content}]
            temperature: Температура генерации
            max_tokens: Лимит токенов
            **kwargs: Доп. параметры API

        Returns:
            dict с ответом API

        Raises:
            LLMError: при неуспешном запросе после всех retry
        """
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            start_time = time.monotonic()
            try:
                response = await client.post(
                    "/chat/completions",
                    json=payload,
                )

                elapsed = time.monotonic() - start_time

                # Успешный ответ
                if response.status_code == 200:
                    data = response.json()
                    logger.info(
                        f"✅ [{self.name}] ответ за {elapsed:.1f}с "
                        f"(модель={self.model}, попытка={attempt})"
                    )
                    return data

                # 503 — модель загружается (Featherless cold start)
                if response.status_code == 503:
                    logger.warning(
                        f"⏳ [{self.name}] 503 — модель загружается "
                        f"(попытка {attempt}/{self.max_retries}, "
                        f"ожидание {self.retry_delay}с)"
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    raise LLMError(
                        f"[{self.name}] 503 после {self.max_retries} попыток — "
                        f"модель {self.model} не загрузилась"
                    )

                # 429 — rate limit
                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get("Retry-After", "5")
                    )
                    logger.warning(
                        f"🚫 [{self.name}] 429 Rate Limit — "
                        f"ожидание {retry_after}с"
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(retry_after)
                        continue
                    raise LLMError(
                        f"[{self.name}] Rate limit после {self.max_retries} попыток"
                    )

                # Другие ошибки — не ретраим
                error_body = response.text[:500]
                raise LLMError(
                    f"[{self.name}] HTTP {response.status_code}: {error_body}"
                )

            except httpx.TimeoutException as e:
                elapsed = time.monotonic() - start_time
                logger.warning(
                    f"⏱️ [{self.name}] Таймаут {elapsed:.1f}с "
                    f"(попытка {attempt}/{self.max_retries}): {e}"
                )
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(5)
                    continue

            except httpx.NetworkError as e:
                logger.error(f"🔌 [{self.name}] Сетевая ошибка: {e}")
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(5)
                    continue

        raise LLMError(
            f"[{self.name}] Все {self.max_retries} попыток исчерпаны: {last_error}"
        )

    async def close(self):
        """Закрытие httpx-клиента."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.debug(f"[{self.name}] httpx-клиент закрыт")


class LLMService:
    """
    Мультипровайдерный LLM-сервис с автоматическим fallback.

    Использование:
        llm = get_llm_service()
        result = await llm.chat("Привет, расскажи про Таро")
    """

    def __init__(self):
        self.providers: list[LLMProvider] = []
        self._init_providers()

    def _init_providers(self):
        """Инициализация провайдеров из конфига в порядке приоритета."""

        # 1. Featherless AI (приоритет)
        if settings.featherless.enabled:
            self.providers.append(LLMProvider(
                name="Featherless",
                api_key=settings.featherless.api_key,
                base_url=settings.featherless.base_url,
                model=settings.featherless.model,
                timeout=settings.featherless.timeout,         # 180с
                max_retries=settings.featherless.max_retries,  # 3
                retry_delay=30.0,
            ))
            logger.info(
                f"🪶 Featherless: модель={settings.featherless.model}, "
                f"таймаут={settings.featherless.timeout}с"
            )

        # 2. Perplexity (фоллбэк #1)
        if settings.perplexity.enabled:
            self.providers.append(LLMProvider(
                name="Perplexity",
                api_key=settings.perplexity.api_key,
                base_url=settings.perplexity.base_url,
                model=settings.perplexity.model,
                timeout=settings.perplexity.timeout,
                max_retries=2,
                retry_delay=5.0,
            ))
            logger.info(f"🔍 Perplexity: модель={settings.perplexity.model}")

        # 3. OpenAI (фоллбэк #2)
        if settings.openai.enabled:
            self.providers.append(LLMProvider(
                name="OpenAI",
                api_key=settings.openai.api_key,
                base_url=settings.openai.base_url,
                model=settings.openai.model,
                timeout=settings.openai.timeout,
                max_retries=2,
                retry_delay=5.0,
            ))
            logger.info(f"🤖 OpenAI: модель={settings.openai.model}")

        if not self.providers:
            logger.error("❌ Ни один LLM-провайдер не настроен!")

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        preferred_provider: Optional[str] = None,
        **kwargs,
    ) -> dict:
        """
        Запрос к LLM с автоматическим fallback.

        Args:
            messages: Список сообщений
            temperature: Температура
            max_tokens: Лимит токенов
            preferred_provider: Принудительный выбор провайдера (по имени)
            **kwargs: Доп. параметры

        Returns:
            dict — ответ API

        Raises:
            AllProvidersFailedError: если все провайдеры упали
        """
        errors: list[str] = []

        # Сортировка: preferred_provider первым
        providers = self.providers
        if preferred_provider:
            providers = sorted(
                self.providers,
                key=lambda p: p.name.lower() != preferred_provider.lower(),
            )

        for provider in providers:
            try:
                return await provider.chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            except LLMError as e:
                error_msg = str(e)
                errors.append(error_msg)
                logger.warning(
                    f"⚠️ [{provider.name}] не удалось — "
                    f"переключаюсь на следующий провайдер: {error_msg}"
                )
                continue

        raise AllProvidersFailedError(
            f"Все провайдеры недоступны:\n" +
            "\n".join(f"  • {e}" for e in errors)
        )

    async def chat(
        self,
        user_message: str,
        system_prompt: str = "Ты — мистический помощник MysticBot.",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> str:
        """
        Упрощённый метод: текст → текст.

        Args:
            user_message: Сообщение пользователя
            system_prompt: Системный промпт

        Returns:
            str — текст ответа
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        data = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        # Извлекаем текст ответа
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"❌ Неожиданный формат ответа: {e}\nData: {data}")
            raise LLMError(f"Неожиданный формат ответа LLM: {e}")

    async def health_check(self) -> dict[str, bool]:
        """
        Проверка доступности каждого провайдера.

        Returns:
            {"Featherless": True, "Perplexity": False, ...}
        """
        results = {}
        for provider in self.providers:
            try:
                await provider.chat_completion(
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5,
                    temperature=0.0,
                )
                results[provider.name] = True
            except Exception:
                results[provider.name] = False
        return results

    async def close(self):
        """Закрытие всех httpx-клиентов."""
        for provider in self.providers:
            await provider.close()
        logger.info("🔒 Все LLM-клиенты закрыты")


# === Синглтон ===
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Получение/создание единственного экземпляра LLMService."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
