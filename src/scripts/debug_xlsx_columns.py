"""Диагностика колонок Excel при загрузке категорий."""
import pandas as pd

path = "КатегорииФарма_ver_1.xlsx"
df = pd.read_excel(path, sheet_name=0)

print("Columns in Excel (repr for exact chars):")
for i, c in enumerate(df.columns):
    print(f"  [{i}] {repr(c)}")

print("\nColumn mapping check:")
column_mapping = {
    "Код категории": "code",
    "Уровень иерархии": "level",
    "Направление": "direction",
    "Потребность / Нозология": "need",
    "Категория": "category",
    "МНН-кластер": "inn_cluster",
    "Тип препарата / товара": "product_type",
    "Возрастной сегмент": "age_segment",
}
for src, dst in column_mapping.items():
    match = src in df.columns
    print(f"  '{src}' -> '{dst}': {'OK' if match else 'NOT FOUND'}")

# Поиск похожих на МНН
print("\nColumns containing МНН/cluster:")
for c in df.columns:
    if "МНН" in c or "мнн" in c or "cluster" in c.lower() or "кластер" in c.lower():
        print(f"  {repr(c)}")
        # Коды символов в колонке Excel
        for i, ch in enumerate(c):
            if ch == "-" or ord(ch) in (0x2010, 0x2011, 0x2212, 0xFE58, 0x002D):
                print(f"    char[{i}] = {repr(ch)} U+{ord(ch):04X}")

# Сравнение: наш ключ vs колонка из Excel
excel_col = [x for x in df.columns if "МНН" in x and "кластер" in x][0]
our_key = "МНН-кластер"
print(f"\nByte/char comparison:")
print(f"  Our key:    {[hex(ord(c)) for c in our_key]}")
print(f"  Excel col:  {[hex(ord(c)) for c in excel_col]}")
