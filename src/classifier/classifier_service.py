# src/classifier/classifier_service.py
from __future__ import annotations

from typing import Optional, List

from src.config import config
from src.data_models import SKU, ClassificationResult, Category
from src.llm_client.base import LLMClient


class ClassifierService:
    """
    Сервис классификации SKU.

    Отвечает за:
    - вызов LLM-клиента;
    - интерпретацию результата;
    - применение порогов уверенности и установку needs_review
      с учётом количества категорий внутри МНН-кластера.
    """

    def __init__(self, llm_client: LLMClient, categories: List[Category]) -> None:
        self._llm_client = llm_client
        self._categories = categories
        self._conf_threshold = config.classifier.confidence_threshold
        self._hard_reject_threshold = config.classifier.hard_reject_threshold

    async def classify_product(self, sku: SKU) -> ClassificationResult:
        """
        Классифицирует один SKU:
        - вызывает LLM;
        - применяет пороговую логику;
        - применяет «multi-cluster safety» для МНН-кластеров с несколькими кодами.
        """
        raw_result = await self._llm_client.classify_sku(sku)
        result = raw_result  # предполагаем, что LLM уже вернул ClassificationResult-совместный объект

        # 1) базовое решение по порогам confidence
        needs_review_by_conf = self._should_mark_needs_review(result.confidence)

        # 2) учесть явный hint модели
        model_hint = bool(result.needs_review)

        result.needs_review = model_hint or needs_review_by_conf

        # 3) дополнительная защита: если в МНН-кластере несколько категорий,
        #    не позволяем высокой уверенности без ревью
        result = self._apply_multi_cluster_safety(result)

        return result

    def _should_mark_needs_review(self, confidence: float) -> bool:
        """
        Логика установки флага needs_review по порогам уверенности.
        """
        if confidence < self._hard_reject_threshold:
            # Совсем низкая уверенность — обязательно на ревью.
            # В будущем здесь можно вообще не присваивать категорию.
            return True

        if confidence < self._conf_threshold:
            # Уверенность средняя — тоже просим ревью.
            return True

        return False

    # ---------- Логика для «тонких» развилок внутри МНН-кластера ----------

    def _get_categories_for_inn(self, detected_inn: Optional[str]) -> list[Category]:
        """
        Возвращает все категории, чьи inn_cluster соответствует найденному МНН
        (с учётом вариантов записи через слэш и разных регистров).
        """
        if not detected_inn:
            return []

        norm_inn = detected_inn.strip().lower()
        matched: list[Category] = []

        for cat in self._categories:
            if not getattr(cat, "inn_cluster", None):
                continue

            cluster_str = cat.inn_cluster.lower()

            # поддерживаем конструкции вида "Римантадин/Rimantadine"
            parts = [p.strip() for p in cluster_str.replace("\\", "/").split("/")]

            if norm_inn in parts:
                matched.append(cat)

        return matched

    def _apply_multi_cluster_safety(self, result: ClassificationResult) -> ClassificationResult:
        """
        Применяет «консервативное» правило для МНН-кластеров с несколькими кодами.

        Идея:
        - если для найденного МНН в дереве категорий существует >1 строка с этим inn_cluster,
          считаем, что внутри кластера есть тонкие различия (*_01, *_02 и т.п.);
        - в такой ситуации решение не должно быть высоко уверенным и без ревью.
        """
        matched_cats = self._get_categories_for_inn(result.inn)
        if len(matched_cats) <= 1:
            # В кластере нет развилки — ничего дополнительно не делаем.
            return result

        # Если модель не поставила needs_review, но внутри кластера несколько вариантов — ставим.
        if not result.needs_review:
            result.needs_review = True

        # Ограничиваем верхнюю границу confidence для таких случаев.
        if result.confidence > 0.6:
            result.confidence = 0.6

        # Добавляем пояснение в reason (аккуратно, чтобы не задвоить текст при повторных вызовах).
        extra_note = (
            f" Дополнительно: для МНН '{result.inn}' в дереве категорий найдено "
            f"{len(matched_cats)} строк в одном МНН-кластере, поэтому решение "
            f"помечено как требующее ревью и уверенность ограничена."
        )
        if result.reason:
            if extra_note not in result.reason:
                result.reason = result.reason.rstrip() + extra_note
        else:
            result.reason = extra_note.lstrip()

        return result
