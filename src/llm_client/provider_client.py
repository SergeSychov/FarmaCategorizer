# src/llm_client/provider_client.py
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import httpx

from src.config import config
from src.data_models import SKU, ClassificationResult
from src.llm_client.base import LLMClient, LLMError, LLMRetryableError
from src.classifier.prompt_builder import PromptBuilder


class ProviderLLMClient(LLMClient):
    """
    Реализация LLMClient через HTTP API провайдера.
    """

    def __init__(self) -> None:
        self._base_url = config.llm.base_url
        self._api_key = os.getenv(config.llm.api_key_env_var, "")
        if not self._api_key:
            # Важно: не падаем молча, а даём явную ошибку конфигурации
            raise LLMError(f"Missing API key in env var {config.llm.api_key_env_var}")

        self._timeout = config.llm.timeout_seconds
        self._retry_conf = config.llm.retry
        self._prompt_builder = PromptBuilder()

    async def _post_with_retries(self, endpoint: str, json: Dict[str, Any]) -> httpx.Response:
        """
        Базовый метод отправки POST-запросов с ретраями по 5xx/429/timeout.
        """
        url = f"{self._base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        attempt = 0
        last_exc: Exception | None = None

        while attempt <= self._retry_conf.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(url, json=json, headers=self._build_headers())

                # Повторяем при 5xx/429, если разрешено конфигом
                if response.status_code >= 500 and self._retry_conf.retry_on_5xx:
                    attempt += 1
                    if attempt > self._retry_conf.max_retries:
                        break
                    await self._sleep_backoff(attempt)
                    continue

                if response.status_code == 429 and self._retry_conf.retry_on_429:
                    attempt += 1
                    if attempt > self._retry_conf.max_retries:
                        break
                    await self._sleep_backoff(attempt)
                    continue

                return response

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if not self._retry_conf.retry_on_timeout:
                    break
                attempt += 1
                if attempt > self._retry_conf.max_retries:
                    break
                await self._sleep_backoff(attempt)

        # Если сюда дошли — ретраи не помогли
        if last_exc is not None:
            raise LLMRetryableError(f"Request to {url} failed after retries") from last_exc

        raise LLMRetryableError(f"Request to {url} failed with status {response.status_code}")  # type: ignore[name-defined]

    async def _sleep_backoff(self, attempt: int) -> None:
        # Простейший линейный/экспоненциальный backoff
        delay = self._retry_conf.backoff_factor * attempt
        await asyncio.sleep(delay)

    def _build_headers(self) -> Dict[str, str]:
        # TODO: адаптировать под конкретного провайдера (Bearer, ключ в заголовке и т.п.)
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def classify_sku_raw(self, sku_name: str) -> Dict[str, Any]:
        """
        Формирует промпт, отправляет запрос к LLM и возвращает JSON-ответ как dict.
        """
        # TODO: сюда нужно будет передавать реальный список категорий,
        # пока передаем пустой, чтобы сделать скелет.
        sku = SKU(name=sku_name)
        categories: list = []

        user_prompt = self._prompt_builder.build_user_prompt(sku, categories)

        payload: Dict[str, Any] = {
            "model": "your-model-name",  # TODO: вынести в конфиг
            "messages": [
                {"role": "system", "content": self._prompt_builder.PROMPT_SYSTEM_INSTRUCTIONS}  # type: ignore[attr-defined]
                if hasattr(self._prompt_builder, "PROMPT_SYSTEM_INSTRUCTIONS")
                else {"role": "system", "content": ""},
                {"role": "user", "content": user_prompt},
            ],
        }

        response = await self._post_with_retries(endpoint="/chat/completions", json=payload)

        if response.status_code >= 400:
            # Неретрайные ошибки / окончательный фейл
            raise LLMError(f"LLM API returned HTTP {response.status_code}: {response.text}")

        # Здесь предполагаем, что провайдер вернёт JSON с нашим полем "content" или сразу JSON-строку
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("Failed to parse LLM response as JSON") from exc

        # TODO: адаптировать под реальный формат ответа провайдера
        # Пока считаем, что data уже является тем JSON, который описан в PROMPT_OUTPUT_FORMAT
        return data

    async def classify_sku(self, sku: SKU) -> ClassificationResult:
        """
        Высокоуровневый метод: вызывает LLM и маппит ответ в ClassificationResult.
        """
        raw = await self.classify_sku_raw(sku.name)

        # Защита от отсутствующих полей
        confidence = float(raw.get("confidence", 0.0))

        result = ClassificationResult(
            sku_name=sku.name,
            category_code=raw.get("category_code"),
            category_path=raw.get("category_path"),
            inn=raw.get("inn"),
            dosage_form=raw.get("dosage_form"),
            age_restriction=raw.get("age_restriction"),
            otc=raw.get("otc"),
            confidence=confidence,
            needs_review=bool(raw.get("needs_review_hint", False)),
            reason=raw.get("reason", ""),
            raw_llm_response=raw,
        )

        return result
