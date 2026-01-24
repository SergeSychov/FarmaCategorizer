# src/classifier/classifier_service.py
from __future__ import annotations

from typing import Optional

from src.config import config
from src.data_models import SKU, ClassificationResult
from src.llm_client.base import LLMClient


class ClassifierService:
    """
    Сервис классификации SKU.

    Отвечает за:
    - вызов LLM-клиента;
    - интерпретацию результата;
    - применение порогов уверенности и установку needs_review.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client
        self._conf_threshold = config.classifier.confidence_threshold
        self._hard_reject_threshold = config.classifier.hard_reject_threshold

    async def classify_product(self, sku: SKU) -> ClassificationResult:
        raw_result = await self._llm_client.classify_sku(sku)
        result = raw_result

        # Базовое решение по порогам
        needs_review_by_conf = self._should_mark_needs_review(result.confidence)

        # Если модель явно просит ревью — уважаем это
        model_hint = bool(result.needs_review)

        result.needs_review = model_hint or needs_review_by_conf
        return result

    def _should_mark_needs_review(self, confidence: float) -> bool:
        """
        Логика установки флага needs_review по порогам уверенности.
        """
        if confidence < self._hard_reject_threshold:
            # Совсем низкая уверенность — обязательно на ревью,
            # возможно, позже будем вообще не присваивать категорию.
            return True

        if confidence < self._conf_threshold:
            # Уверенность средняя — тоже просим ревью.
            return True

        return False
