# src/scripts/debug_one_sku.py
import asyncio

from src.io.db_io import get_session, get_active_product_links, product_link_to_sku
from src.llm_client.provider_client import ProviderLLMClient
from src.classifier.prompt_builder import PromptBuilder
from src.io.db_io import get_all_categories


async def main() -> None:
    # Берём один product_link из БД
    with get_session() as session:
        categories = get_all_categories(session)
        product_links = get_active_product_links(session, limit=1)
        pl = product_links[0]
        sku = product_link_to_sku(pl)

    client = ProviderLLMClient(categories=categories)
    raw = await client.classify_sku_raw(sku.name)

    print("SKU:", sku.name)
    print("RAW:", raw)


if __name__ == "__main__":
    asyncio.run(main())
