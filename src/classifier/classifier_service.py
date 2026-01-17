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
        """
        Основной метод, который будет вызываться внешним кодом.

        TODO: когда появится формат JSON-ответа от LLM, здесь нужно будет:
        - вызвать llm_client.classify_sku_raw или classify_sku;
        - разобрать JSON;
        - оценить confidence;
        - заполнить ClassificationResult и флаг needs_review.
        """
        # Пока простая заглушка, чтобы была рабочая структура.
        # Позже будет реальная логика маппинга полей.
        raw_result = await self._llm_client.classify_sku(sku)

        # На первом шаге считаем, что LLM уже вернул корректный ClassificationResult.
        # В будущем сюда можно добавить дополнительную пост-обработку.
        result = raw_result

        # Применяем пороги уверенности
        needs_review = self._should_mark_needs_review(result.confidence)
        result.needs_review = needs_review

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
