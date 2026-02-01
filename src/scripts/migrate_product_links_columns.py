# src/scripts/migrate_product_links_columns.py
"""
Миграция БД: добавление колонок в product_links и categories.
Запуск: python -m src.scripts.migrate_product_links_columns
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("pharmacy_analyzer/data/linkages.db")


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- product_links ---
    product_links_columns = [
        ("category_code", "TEXT"),
        ("category_path", "TEXT"),
        ("inn", "TEXT"),
        ("dosage_form", "TEXT"),
        ("age_restriction", "TEXT"),
        ("otc", "INTEGER"),
        ("confidence", "REAL"),
        ("needs_review", "INTEGER"),
        ("classification_reason", "TEXT"),
    ]

    for name, coltype in product_links_columns:
        if not column_exists(cur, "product_links", name):
            print(f"product_links: adding column {name} ({coltype})")
            cur.execute(f"ALTER TABLE product_links ADD COLUMN {name} {coltype};")
        else:
            print(f"product_links: column {name} already exists")

    # --- categories: inn_cluster ---
    if table_exists(cur, "categories"):
        if not column_exists(cur, "categories", "inn_cluster"):
            print("categories: adding column inn_cluster (TEXT)")
            cur.execute("ALTER TABLE categories ADD COLUMN inn_cluster TEXT;")
        else:
            print("categories: column inn_cluster already exists")
    else:
        print("categories: table does not exist, skipping (will be created by load_categories_from_xlsx)")

    conn.commit()
    conn.close()
    print("Migration finished.")


if __name__ == "__main__":
    main()
