# src/io/db_io.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, List

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.data_models import SKU, ClassificationResult

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
    """
    return SKU(
        name=pl.name_1c,
        external_id=str(pl.id),
        manufacturer=pl.manufacturer_1c,
        alt_name=pl.name_asna,
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
