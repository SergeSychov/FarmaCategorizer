# src/data_models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SKU:
    """
    Минимальное описание SKU из базы.

    Пока гарантировано только name, остальные поля могут добавиться позже
    (ID из БД, код категории из исходной выгрузки и т.п.).
    """
    name: str
    external_id: Optional[str] = None  # например, ID в региональной базе


@dataclass
class Category:
    """
    Категория из аптечного классификатора.

    TODO: синхронизировать поля с реальными колонками из xlsx/CSV классификатора.
    """
    code: str
    level: Optional[str] = None
    direction: Optional[str] = None
    need: Optional[str] = None
    group: Optional[str] = None
    inn_cluster: Optional[str] = None
    dosage_form: Optional[str] = None
    age_segment: Optional[str] = None


@dataclass
class ClassificationResult:
    """
    Результат классификации одного SKU.
    """
    sku_name: str
    category_code: Optional[str]
    category_path: Optional[str]  # Человекочитаемый путь по дереву категорий
    inn: Optional[str]  # МНН / действующее вещество (если найдено)
    dosage_form: Optional[str]
    age_restriction: Optional[str]
    otc: Optional[bool]  # True = OTC, False = Rx, None = неизвестно

    confidence: float  # Оценка уверенности 0..1
    needs_review: bool  # Флаг, что результат должен проверить эксперт
    reason: str  # Краткое текстовое обоснование (почему выбрана категория/флаг review)

    raw_llm_response: Optional[dict] = None  # Для отладки и аудита


@dataclass
class SKU:
    """
    Минимальное описание SKU из базы.
    """
    name: str
    external_id: Optional[str] = None  # например, id ProductLink
    manufacturer: Optional[str] = None
    alt_name: Optional[str] = None  # name_asna или другое альтернативное имя
