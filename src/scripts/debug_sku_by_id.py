# src/scripts/debug_sku_by_id.py
import asyncio

from src.io.db_io import get_session, ProductLink, product_link_to_sku
from src.llm_client.provider_client import ProviderLLMClient
from src.io.db_io import get_all_categories


async def debug_sku_by_id(product_link_id: int) -> None:
    # 1. Берём запись из БД и строим SKU
    with get_session() as session:
        pl = session.get(ProductLink, product_link_id)
        if pl is None:
            print(f"ProductLink id={product_link_id} not found")
            return

        categories = get_all_categories(session)
        sku = product_link_to_sku(pl)

    # 2. Классифицируем через DeepSeek
    client = ProviderLLMClient(categories=categories)
    raw = await client.classify_sku_raw(sku.name)

    print(f"SKU (id={product_link_id}):", sku.name)
    print("RAW:", raw)


if __name__ == "__main__":
    asyncio.run(debug_sku_by_id(8))
