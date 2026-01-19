# src/scripts/run_batch_classification.py
import asyncio
from typing import List

from src.config import make_llm_config
from src.data_models import SKU, ClassificationResult, Category
from src.llm_client.provider_client import ProviderLLMClient
from src.classifier.classifier_service import ClassifierService
from src.io.db_io import (
    get_session,
    get_active_product_links,
    product_link_to_sku,
    save_classification_result,
    get_all_categories,
)


async def classify_batch(limit: int = 20) -> None:
    with get_session() as session:
        categories: List[Category] = get_all_categories(session)
        product_links = get_active_product_links(session, limit=limit)

        llm_config = make_llm_config()
        llm_client = ProviderLLMClient(categories=categories, config=llm_config)
        service = ClassifierService(llm_client=llm_client)

        for pl in product_links:
            sku: SKU = product_link_to_sku(pl)
            result: ClassificationResult = await service.classify_product(sku)
            save_classification_result(session, pl.id, result)


def main() -> int:
    asyncio.run(classify_batch(limit=20))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
