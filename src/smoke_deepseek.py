# src/smoke_deepseek.py
import asyncio

from src.llm_client.provider_client import ProviderLLMClient
from src.data_models import Category
from src.config import config


async def main():
    # Пока можно пустой список категорий
    categories: list[Category] = []

    client = ProviderLLMClient(categories=categories)

    raw = await client.classify_sku_raw("Нурофен Форте, таблетки")
    print("RAW LLM RESPONSE:", raw)


if __name__ == "__main__":
    asyncio.run(main())