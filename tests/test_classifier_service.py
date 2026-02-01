# tests/test_classifier_service.py
import asyncio
from unittest.mock import AsyncMock

from src.classifier.classifier_service import ClassifierService
from src.data_models import SKU, ClassificationResult
from src.llm_client.base import LLMClient


class DummyLLMClient(LLMClient):
    async def classify_sku_raw(self, sku_name: str):
        raise NotImplementedError

    async def classify_sku(self, sku: SKU) -> ClassificationResult:
        raise NotImplementedError


def test_classifier_marks_needs_review_for_low_confidence():
    client = DummyLLMClient()

    fake_result = ClassificationResult(
        sku_name="TEST SKU",
        category_code="CAT001",
        category_path="Направление > Группа",
        inn="Test INN",
        dosage_form="таблетки",
        age_restriction="18+",
        otc=True,
        confidence=0.3,
        needs_review=False,
        reason="low confidence",
        raw_llm_response={"dummy": True},
    )

    client.classify_sku = AsyncMock(return_value=fake_result)

    service = ClassifierService(llm_client=client, categories=[])

    result = asyncio.run(service.classify_product(SKU(name="TEST SKU")))

    assert result.needs_review is True
    assert result.confidence == 0.3
