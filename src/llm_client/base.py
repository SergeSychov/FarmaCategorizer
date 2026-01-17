# src/llm_client/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

#from src.data_models import SKU, ClassificationResult  # создадим позже


class LLMError(Exception):
    """Базовая ошибка LLM-клиента."""


class LLMRetryableError(LLMError):
    """Ошибки, при которых можно безопасно повторить запрос (5xx, 429, timeout)."""


class LLMClient(ABC):
    """
    Абстракция LLM-клиента.

    Задачи:
    - принять название SKU;
    - сходить к LLM (с веб-поиском по возможности);
    - вернуть структурированный JSON с извлеченными полями (МНН, форма, возраст, OTC/Rx).
    """

    @abstractmethod
    async def classify_sku_raw(self, sku_name: str) -> Dict[str, Any]:
        """
        Вызов LLM и возврат «сырого» структурированного ответа (dict),
        без привязки к внутренним моделям проекта.

        Здесь должны обрабатываться:
        - ретраи;
        - таймауты;
        - маппинг HTTP/сетевых ошибок в LLMError/LLMRetryableError.
        """
        raise NotImplementedError

    @abstractmethod
    async def classify_sku(self, sku: SKU) -> ClassificationResult:
        """
        Высокоуровневая обертка над classify_sku_raw:
        - вызывает LLM;
        - маппит ответ в ClassificationResult;
        - НЕ принимает решений по порогам уверенности (это задача classifier_service).
        """
        raise NotImplementedError
