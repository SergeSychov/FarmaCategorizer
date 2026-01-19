import asyncio

from src.config import config
from src.llm_client.provider_client import ProviderLLMClient
from src.data_models import Category, SKU

async def main():
    categories = []  # можно временно пустой список
    client = ProviderLLMClient(categories=categories)

    raw = await client.classify_sku_raw("Нурофен Форте, таблетки")
    print("RAW:", raw)

if __name__ == "__main__":
    asyncio.run(main())
