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

    required_cols = [
        "Название",
        "Производитель",
        "Название АСНА",
        "МНН",
        "Код категории",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in testset: {missing}")

    # Убираем полностью пустые SKU (без названия)
    df = df[~df["Название"].isna()]

    # Нормализуем NaN -> пустая строка, чтобы str(...) не давал "nan"
    for col in ["Название", "Производитель", "Название АСНА", "МНН", "Код категории"]:
        df[col] = df[col].fillna("")

    return df


async def evaluate_on_testset(limit: int = 50) -> None:
    """
    Оценивает качество классификации на TestButch.xlsx.

    Считает:
    - accuracy по category_code;
    - долю needs_review=True;
    - долю точных совпадений МНН (после нормализации строки);
    - выводит примеры расхождений.
    """
    df = load_testset()

    # Ограничиваем выборку для первых прогонов (случайная выборка)
    n = min(limit, len(df))
    df = df.sample(n=n, random_state=24).reset_index(drop=True)

    # Загружаем дерево категорий
    with get_session() as session:
        categories: List[Category] = get_all_categories(session)

    client = ProviderLLMClient(categories=categories)
    service = ClassifierService(llm_client=client, categories=categories)

    total = 0
    correct_cat = 0
    needs_review_count = 0

    inn_match = 0
    total_with_true_inn = 0

    # (true_code, pred_code, true_inn, pred_inn, sku_name, reason)
    results: List[Tuple[str, str, str, str, str, str]] = []

    def norm(s: str) -> str:
        """Простая нормализация строк: trim, lower, схлопнуть пробелы."""
        return " ".join(str(s).strip().lower().split())

    for idx, (_, row) in enumerate(df.iterrows(), start=1):

        name = str(row["Название"]).strip()
        if not name:
            # пропускаем строки без названия на всякий случай
            continue

        print(f"Processing sample {idx}/{len(df)}...")
        sku = SKU(
            name=name,
            manufacturer=str(row.get("Производитель") or ""),
            alt_name=str(row.get("Название АСНА") or ""),
        )
        true_code = str(row.get("Код категории") or "").strip()
        true_inn_raw = row.get("МНН") or ""
        true_inn = norm(true_inn_raw)

        result: ClassificationResult = await service.classify_product(sku)

        total += 1

        # Метрика по категории
        pred_code = (result.category_code or "").strip()
        if true_code and pred_code and pred_code == true_code:
            correct_cat += 1

        # Метрика по needs_review
        if result.needs_review:
            needs_review_count += 1

        # Метрика по МНН
        pred_inn = norm(result.inn or "")
        if true_inn:
            total_with_true_inn += 1
            if pred_inn and pred_inn == true_inn:
                inn_match += 1

        results.append(
            (
                true_code,
                pred_code,
                true_inn,
                pred_inn,
                sku.name,
                result.reason or "",
            )
        )

    accuracy_cat = correct_cat / total if total else 0.0
    review_rate = needs_review_count / total if total else 0.0
    inn_accuracy = inn_match / total_with_true_inn if total_with_true_inn else 0.0

    print(f"Total samples: {total}")
    print(f"Accuracy by category_code: {accuracy_cat:.3f}")
    print(f"Share with needs_review=True: {review_rate:.3f}")
    print(f"INN exact match (normalized, where true INN present): {inn_accuracy:.3f}")

    # Вывод нескольких расхождений по категории
    print("\nExamples of mismatches (up to 10):")
    shown = 0
    for true_code, pred_code, true_inn, pred_inn, sku_name, reason in results:
        if true_code != pred_code and shown < 10:
            print("-" * 80)
            print(f"SKU: {sku_name}")
            print(f"TRUE code: {true_code} | PRED code: {pred_code}")
            print(f"TRUE INN: {true_inn} | PRED INN: {pred_inn}")
            print(f"Reason: {reason}")
            shown += 1
        if shown >= 10:
            break



def main() -> int:
    asyncio.run(evaluate_on_testset(limit=10))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
