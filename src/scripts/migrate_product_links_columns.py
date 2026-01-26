# src/scripts/migrate_product_links_columns.py
from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path("pharmacy_analyzer/data/linkages.db")


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    columns_to_add = [
        ("category_code", "TEXT"),
        ("category_path", "TEXT"),
        ("inn", "TEXT"),
        ("dosage_form", "TEXT"),
        ("age_restriction", "TEXT"),
        ("otc", "INTEGER"),           # 0/1 как bool
        ("confidence", "REAL"),
        ("needs_review", "INTEGER"),  # 0/1 как bool
        ("classification_reason", "TEXT"),
    ]

    for name, coltype in columns_to_add:
        if not column_exists(cur, "product_links", name):
            print(f"Adding column {name} {coltype}")
            cur.execute(f"ALTER TABLE product_links ADD COLUMN {name} {coltype};")
        else:
            print(f"Column {name} already exists, skipping")

    conn.commit()
    conn.close()
    print("Migration finished.")


if __name__ == "__main__":
    main()
