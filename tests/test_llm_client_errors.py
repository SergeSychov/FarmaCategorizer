# tests/test_llm_client_errors.py
import asyncio

import httpx
import pytest

from src.llm_client.provider_client import ProviderLLMClient
from src.llm_client.base import LLMRetryableError, LLMError


@pytest.fixture(autouse=True)
def set_dummy_env(monkeypatch):
    # Подставляем фейковый API-ключ, чтобы не зависеть от реального окружения
    monkeypatch.setenv("LLM_API_KEY", "test-key")


def test_retryable_error_on_timeout(monkeypatch):
    async def fake_post_with_retries(self, endpoint, json):
        raise LLMRetryableError("timeout")

    # Патчим только внутренний метод, чтобы не трогать httpx
    monkeypatch.setattr(
        "src.llm_client.provider_client.ProviderLLMClient._post_with_retries",
        fake_post_with_retries,
    )

    client = ProviderLLMClient()

    with pytest.raises(LLMRetryableError):
        asyncio.run(client.classify_sku_raw("TEST SKU"))


def test_llm_error_on_http_error(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code: int, text: str = ""):
            self.status_code = status_code
            self.text = text

        def json(self):
            return {}

    async def fake_post_with_retries(self, endpoint, json):
        return DummyResponse(status_code=500, text="internal error")

    monkeypatch.setattr(
        "src.llm_client.provider_client.ProviderLLMClient._post_with_retries",
        fake_post_with_retries,
    )

    client = ProviderLLMClient()

    with pytest.raises(LLMError):
        asyncio.run(client.classify_sku_raw("TEST SKU"))
