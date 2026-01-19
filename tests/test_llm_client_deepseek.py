import json
import pytest
from pytest_httpx import HTTPXMock

from src.llm_client.provider_client import ProviderLLMClient
from src.config import config
from src.data_models import Category, SKU
from src.llm_client.base import LLMError


@pytest.mark.asyncio
async def test_deepseek_classify_sku_raw_ok(httpx_mock: HTTPXMock, monkeypatch):
    # Подготовка категорий (можно проще, если есть фабрики)
    categories = [
        Category(
        code="A01",
        level="Категория",
        direction="Обезболивающие",
        need="Боль",
        group="Обезболивающие препараты",
        inn_cluster="Ибупрофен",
        dosage_form="таблетки",
        age_segment="Взрослые",
        )
    ]

    # Ожидаемое тело запроса (частично)
    def match_request(request):
        body = json.loads(request.content)
        assert body["model"] == config.llm.model
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"
        return True

    # Ответ DeepSeek: JSON внутри content
    llm_payload = {
        "category_code": "A01",
        "category_path": "A01 > Препараты от боли",
        "inn": "Ибупрофен",
        "dosage_form": "таблетки",
        "age_restriction": "12+",
        "otc": True,
        "confidence": 0.9,
        "needs_review_hint": False,
        "reason": "Ясная формулировка и соответствие категории",
    }

    httpx_mock.add_response(
    method="POST",
    url=f"{config.llm.base_url.rstrip('/')}/{config.llm.endpoint.lstrip('/')}",
    json={
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(llm_payload),
                },
                "finish_reason": "stop",
            }
        ],
    },
)


    client = ProviderLLMClient(categories=categories)
    raw = await client.classify_sku_raw("Нурофен Форте, таблетки")

    assert raw["category_code"] == "A01"
    assert raw["inn"] == "Ибупрофен"
    assert raw["confidence"] == 0.9

@pytest.mark.asyncio
async def test_deepseek_classify_sku_raw_bad_json(httpx_mock: HTTPXMock):
    categories = []

    httpx_mock.add_response(
        method="POST",
        url=f"{config.llm.base_url.rstrip('/')}/{config.llm.endpoint.lstrip('/')}",
        json={
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "{not valid json",
                    },
                    "finish_reason": "stop",
                }
            ],
        },
    )

    client = ProviderLLMClient(categories=categories)
    with pytest.raises(LLMError):
        await client.classify_sku_raw("Что‑то")
