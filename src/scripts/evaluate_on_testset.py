# src/scripts/evaluate_on_testset.py
import asyncio
from typing import List, Tuple

import pandas as pd

from src.data_models import SKU, ClassificationResult, Category
from src.llm_client.provider_client import ProviderLLMClient
from src.classifier.classifier_service import ClassifierService
from src.io.db_io import get_session, get_all_categories


TESTSET_PATH = "TestButch.xlsx"


def load_testset(path: str = TESTSET_PATH) -> pd.DataFrame:
    df = pd.read_excel(path)

    # TODO: подправить названия колонок под реальные (если отличаются)
    required_cols = [
        "Название",          # name_1c
        "Производитель",     # manufacturer_1c
        "Название АСНА",     # name_asna
        "МНН",               # эталонное МНН
        "Код категории",     # эталонный код категории
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in testset: {missing}")

    return df


async def evaluate_on_testset(limit: int = 50) -> None:
    df = load_testset()

    # Ограничим выборку для первых прогонов
    df = df.head(limit)

    with get_session() as session:
        categories: List[Category] = get_all_categories(session)

    client = ProviderLLMClient(categories=categories)
    service = ClassifierService(llm_client=client)

    total = 0
    correct = 0
    needs_review_count = 0

    results: List[Tuple[str, str, str]] = []  # (true_code, pred_code, reason)

    for _, row in df.iterrows():
        sku = SKU(
            name=str(row["Название"]),
            manufacturer=str(row.get("Производитель") or ""),
            alt_name=str(row.get("Название АСНА") or ""),
        )
        true_code = str(row.get("Код категории") or "")

        result: ClassificationResult = await service.classify_product(sku)

        total += 1
        if result.category_code == true_code and true_code:
            correct += 1
        if result.needs_review:
            needs_review_count += 1

        results.append((true_code, result.category_code or "", result.reason))

    accuracy = correct / total if total else 0.0
    review_rate = needs_review_count / total if total else 0.0

    print(f"Total samples: {total}")
    print(f"Accuracy by category_code: {accuracy:.3f}")
    print(f"Share with needs_review=True: {review_rate:.3f}")

    # При необходимости можно вывести несколько примеров расхождений
    for true_code, pred_code, reason in results[:10]:
        if true_code != pred_code:
            print(f"TRUE: {true_code}, PRED: {pred_code}, reason={reason}")


def main() -> int:
    asyncio.run(evaluate_on_testset(limit=20))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
