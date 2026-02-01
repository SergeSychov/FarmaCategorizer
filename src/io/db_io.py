from __future__ import annotations

import pandas as pd

from contextlib import contextmanager
from typing import Iterator, List

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, create_engine, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.data_models import SKU, ClassificationResult

from typing import List
from src.data_models import Category

DATABASE_URL = "sqlite:///pharmacy_analyzer/data/linkages.db"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

Base = declarative_base()


class ProductLink(Base):
    __tablename__ = "product_links"

    id = Column(Integer, primary_key=True, index=True)
    code_1c = Column(Integer, index=True)
    code_asna = Column(Integer, index=True)
    name_1c = Column(String, nullable=False)
    manufacturer_1c = Column(String, nullable=True)
    name_asna = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Поля классификации (TODO: убедиться, что они добавлены в БД миграцией)
    category_code = Column(String, nullable=True)
    category_path = Column(String, nullable=True)
    inn = Column(String, nullable=True)
    dosage_form = Column(String, nullable=True)
    age_restriction = Column(String, nullable=True)
    otc = Column(Boolean, nullable=True)
    confidence = Column(Float, nullable=True)
    needs_review = Column(Boolean, nullable=True)
    classification_reason = Column(String, nullable=True)

class CategoryDB(Base):
    __tablename__ = "categories"

    # code есть в таблице, делаем его PK
    code = Column(String, primary_key=True)  # TEXT
    level = Column(String, nullable=True)  # TEXT
    direction = Column(String, nullable=True)  # TEXT
    need = Column(String, nullable=True)  # TEXT
    category = Column(String, nullable=True)  # TEXT
    inn_cluster = Column(String, nullable=True)  # TEXT, «МНН-кластер» из xlsx
    product_type = Column(String, nullable=True)  # TEXT
    age_segment = Column(String, nullable=True)  # TEXT
    administration_route = Column(String, nullable=True)  # TEXT
    differentiation = Column(String, nullable=True)  # TEXT
    comment = Column(Text, nullable=True)  # TEXT

@contextmanager
def get_session() -> Iterator[Session]:
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def product_link_to_sku(pl: ProductLink) -> SKU:
    """
    Строит SKU из записи product_links.

    Логика:
    - если name_1c пустой или равен "nan" (как текст), берём name_asna;
    - если и там мусор, всё равно используем то, что есть, но LLM, скорее всего, вернёт низкий confidence.
    """
    def _clean_name(value: object) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        # Частый случай: из pandas/Excel попадает строка "nan"
        if s.lower() == "nan":
            return None
        return s

    name_1c = _clean_name(pl.name_1c)
    name_asna = _clean_name(pl.name_asna)

    # Приоритет: нормальное имя из 1С, иначе — ASNA
    name = name_1c or name_asna or "UNKNOWN_SKU"

    return SKU(
        name=name,
        external_id=str(pl.id),
        manufacturer=_clean_name(pl.manufacturer_1c),
        alt_name=name_asna,
    )


def save_classification_result(session: Session, product_link_id: int, result: ClassificationResult) -> None:
    """
    Сохраняет результат классификации в запись product_links.
    """
    pl: ProductLink | None = session.get(ProductLink, product_link_id)
    if pl is None:
        return

    pl.category_code = result.category_code
    pl.category_path = result.category_path
    pl.inn = result.inn
    pl.dosage_form = result.dosage_form
    pl.age_restriction = result.age_restriction
    pl.otc = result.otc
    pl.confidence = result.confidence
    pl.needs_review = result.needs_review
    pl.classification_reason = result.reason


def get_active_product_links(session: Session, limit: int = 100) -> List[ProductLink]:
    """
    Возвращает список активных product_links для классификации.
    """
    return (
        session.query(ProductLink)
        .filter(ProductLink.is_active.is_(True))
        .limit(limit)
        .all()
    )

def _normalize_column_name(name: str) -> str:
    """
    Нормализует название колонки: заменяет Unicode-дефисы (U+2011, U+2010 и т.п.)
    на обычный ASCII-дефис (U+002D). Excel часто использует non-breaking hyphen.
    """
    for char in ("\u2011", "\u2010", "\u2212", "\uFE58", "\u2013"):
        name = name.replace(char, "-")
    return name


def load_categories_from_xlsx(xlsx_path: str, sheet_name: str = 0) -> None:
    """
    Загружает классификатор категорий из xlsx в таблицу categories.

    Ожидается, что в xlsx есть колонки с именами, соответствующими русским заголовкам.
    Маппинг можно будет скорректировать, когда приедет финальный файл.
    """
    df = pd.read_excel(xlsx_path, sheet_name=sheet_name)

    # Нормализуем названия колонок (Excel может использовать U+2011 вместо U+002D)
    df.columns = [_normalize_column_name(str(c)) for c in df.columns]

    # Простейший маппинг колонок xlsx -> поля модели.
    # TODO: скорректировать названия колонок под реальный файл.
    column_mapping = {
        "Код категории": "code",
        "Уровень иерархии": "level",
        "Направление": "direction",
        "Потребность / Нозология": "need",
        "Категория": "category",
        "МНН-кластер": "inn_cluster",
        "Тип препарата / товара": "product_type",
        "Возрастной сегмент": "age_segment",
        "Способ введения": "administration_route",
        "Степень дифференциации категории": "differentiation",
        "Комментарий / правила включения": "comment",
    }

    # Переименуем только те колонки, которые реально есть в файле
    existing_mapping = {
        src: dst for src, dst in column_mapping.items() if src in df.columns
    }
    df = df.rename(columns=existing_mapping)

    # Оставим только те целевые колонки, которые реально получились
    available_targets = [dst for dst in existing_mapping.values() if dst in df.columns]
    df = df[available_targets]

    # Запишем в БД (если таблица уже есть, заменим)
    df.to_sql("categories", con=engine, if_exists="replace", index=False)

def category_db_to_domain(cat_db: CategoryDB) -> Category:
    """
    Маппит ORM-модель CategoryDB в доменный класс Category.
    """
    return Category(
        code=cat_db.code or "",
        level=cat_db.level,
        direction=cat_db.direction,
        need=cat_db.need,
        group=cat_db.category,
        inn_cluster=getattr(cat_db, "inn_cluster", None),
        dosage_form=cat_db.product_type,
        age_segment=cat_db.age_segment,
    )


def get_all_categories(session: Session) -> List[Category]:
    """
    Возвращает все категории классификатора в виде доменных объектов Category.
    Игнорирует возможные None в результате ORM-запроса.
    """
    cats_db = session.query(CategoryDB).all()
    return [
        category_db_to_domain(c)
        for c in cats_db
        if c is not None
    ]