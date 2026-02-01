# src/scripts/run_batch_classification.py
from __future__ import annotations

import asyncio
import logging
from typing import List

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
from src.llm_client.base import LLMError, LLMRetryableError


logger = logging.getLogger(__name__)


async def classify_batch(limit: int = 10) -> None:
    """
    Последовательная batch-классификация product_links из БД.

    Делает:
    - загрузку категорий;
    - инициализацию LLM-клиента и классификатора;
    - обработку product_links с обработкой ошибок;
    - краткий итоговый отчёт.
    """
    logging.basicConfig(level=logging.INFO)

    # get_session здесь синхронный контекстный менеджер, поэтому просто "with"
    with get_session() as session:
        categories: List[Category] = get_all_categories(session)
        product_links = get_active_product_links(session, limit=limit)

        llm_client = ProviderLLMClient(categories=categories)
        service = ClassifierService(llm_client=llm_client, categories=categories)

        total = len(product_links)
        classified_ok = 0
        needs_review_count = 0
        llm_errors = 0
        llm_retryable_errors = 0
        other_errors = 0

        logger.info("Starting batch classification: %s items", total)

        for pl in product_links:
            sku: SKU = product_link_to_sku(pl)

            try:
                result: ClassificationResult = await service.classify_product(sku)
                #save_classification_result(session, pl, result)
                save_classification_result(session, pl.id, result)

                classified_ok += 1
                if result.needs_review:
                    needs_review_count += 1

            except LLMRetryableError as e:
                llm_retryable_errors += 1
                logger.warning(
                    "LLMRetryableError for SKU '%s' (product_link_id=%s): %s",
                    sku.name,
                    getattr(pl, "id", None),
                    e,
                )
                # SKU считается неуспешно обработанным, но цикл продолжается

            except LLMError as e:
                llm_errors += 1
                logger.error(
                    "LLMError for SKU '%s' (product_link_id=%s): %s",
                    sku.name,
                    getattr(pl, "id", None),
                    e,
                )

            except Exception as e:
                other_errors += 1
                logger.exception(
                    "Unexpected error for SKU '%s' (product_link_id=%s): %s",
                    sku.name,
                    getattr(pl, "id", None),
                    e,
                )
        # После обработки всех записей фиксируем изменения
        session.commit()

        logger.info("Batch classification finished.")
        logger.info("Total product_links: %s", total)
        logger.info("Successfully classified: %s", classified_ok)
        logger.info("Marked as needs_review: %s", needs_review_count)
        logger.info("LLM errors: %s", llm_errors)
        logger.info("LLM retryable errors: %s", llm_retryable_errors)
        logger.info("Other errors: %s", other_errors)


def main() -> int:
    asyncio.run(classify_batch(limit=20))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
