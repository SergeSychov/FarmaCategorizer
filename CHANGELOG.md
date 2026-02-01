# Changelog

## 2026-01-26 — Исправления и загрузка МНН-кластера

### Исправления

- **ClassifierService** — добавлен обязательный параметр `categories` в конструктор; скрипты и тесты обновлены.
- **inn_cluster в БД** — добавлена колонка `inn_cluster` в модель `CategoryDB` и маппинг `category_db_to_domain`.
- **Загрузка Excel** — нормализация названий колонок: Unicode-дефис (U+2011) → ASCII-дефис. Колонка «МНН‑кластер» из Excel теперь корректно маппится в `inn_cluster`.
- **data_models.py** — удалено дублирование класса `SKU`.
- **evaluate_on_testset** — защита `df.sample(n=min(limit, len(df)))`, удалён неиспользуемый `import random`.
- **config.py** — удалён дублирующийся комментарий.

### Миграция БД

- `migrate_product_links_columns.py` — добавлена миграция колонки `inn_cluster` в таблицу `categories`.
- После `load_categories_from_xlsx` колонка создаётся автоматически (миграция нужна только если таблица была создана без неё).

### Результаты оценки (TestButch.xlsx, 10 сэмплов)

| Метрика               | До загрузки inn_cluster | После |
|-----------------------|-------------------------|-------|
| Accuracy по category_code | 60%                  | **90%** |
| needs_review=True     | 20%                     | 40%   |
| Точное совпадение МНН | 90%                     | 90%   |

### Добавленные файлы

- `README.md` — описание проекта, архитектура, запуск.
- `ERRORS_ANALYSIS.md` — анализ и статус исправленных ошибок.
- `src/scripts/debug_xlsx_columns.py` — диагностика колонок Excel.
