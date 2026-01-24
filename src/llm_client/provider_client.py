# src/llm_client/provider_client.py
from __future__ import annotations

import asyncio
import os
import json
from typing import Any, Dict

import httpx

from src.config import config
from src.config import LLMApiConfig
from src.data_models import SKU, ClassificationResult, Category
from src.llm_client.base import LLMClient, LLMError, LLMRetryableError
from src.classifier.prompt_builder import PromptBuilder


class ProviderLLMClient(LLMClient):
    """
    Реализация LLMClient через HTTP API провайдера.
    """

    def __init__(self, categories: list[Category] | None = None) -> None:
        self._base_url = config.llm.base_url
        self._api_key = os.getenv(config.llm.api_key_env_var, "")
        if not self._api_key:
            # Важно: не падаем молча, а даём явную ошибку конфигурации
             raise LLMError(f"Missing API key in env var {config.llm.api_key_env_var}")

        self._timeout = config.llm.timeout_seconds
        self._retry_conf = config.llm.retry
        self._prompt_builder = PromptBuilder()
        self._categories: list[Category] = categories or []

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
        sku = SKU(name=sku_name)
        categories = self._categories
        user_prompt = self._prompt_builder.build_user_prompt(sku, categories)

        messages = [
            {
                "role": "system",
                "content": getattr(
                    self._prompt_builder,
                    "PROMPT_SYSTEM_INSTRUCTIONS",
                    "",
                ),
            },
            {"role": "user", "content": user_prompt},
        ]

        payload: Dict[str, Any] = {
            "model": config.llm.model,
            "messages": messages,
            "temperature": 0,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

        response = await self._post_with_retries(
            endpoint=config.llm.endpoint,
            json=payload,
        )

        if response.status_code >= 400:
            raise LLMError(
                f"LLM API returned HTTP {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("Failed to parse LLM response as JSON") from exc

        try:
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise LLMError("Failed to extract JSON from LLM response") from exc

        return parsed

    async def classify_sku(self, sku: SKU) -> ClassificationResult:
        """
        Высокоуровневый метод для классификации одного SKU.

        Делает три вещи:
        1) Вызывает LLM (DeepSeek) и получает сырой JSON-ответ в виде dict.
        2) Аккуратно извлекает поля из raw-ответа и нормализует confidence.
        3) Собирает доменный объект ClassificationResult, который дальше
           будет обрабатываться ClassifierService.
        """
        # 1. Запрашиваем у модели структурированный JSON по названию SKU.
        #    Метод classify_sku_raw уже:
        #    - формирует messages и payload;
        #    - делает HTTP-запрос с ретраями;
        #    - достаёт choices[0].message.content;
        #    - парсит JSON-строку в dict
        raw: Dict[str, Any] = await self.classify_sku_raw(sku.name)

        # 2. Извлекаем confidence и приводим к float с защитой от мусора.
        raw_confidence = raw.get("confidence", 0.0)

        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            # Если модель вернула что-то некорректное, считаем уверенность нулевой.
            confidence = 0.0

        # 2.1. Жёстко ограничиваем confidence в диапазоне [0.0, 1.0],
        #      чтобы пороги в ClassifierService вели себя предсказуемо.
        confidence = max(0.0, min(confidence, 1.0))

        # 3. Собираем ClassificationResult из сырого ответа.
        #    Все поля берём "мягко" через get, чтобы падение по KeyError не ломало пайплайн.
        result = ClassificationResult(
            sku_name=sku.name,
            category_code=raw.get("category_code"),
            category_path=raw.get("category_path"),
            inn=raw.get("inn"),
            dosage_form=raw.get("dosage_form"),
            age_restriction=raw.get("age_restriction"),
            otc=raw.get("otc"),
            confidence=confidence,
            # На этом уровне мы просто сохраняем hint от модели.
            # Окончательное решение по needs_review принимает ClassifierService.
            needs_review=bool(raw.get("needs_review_hint", False)),
            reason=raw.get("reason", "") or "",
            # Сохраняем исходный dict на случай отладки и анализа качества.
            raw_llm_response=raw,
        )

        return result
