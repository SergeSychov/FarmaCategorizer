# Анализ текущих ошибок FarmaCategorizer

> ✅ Все перечисленные ошибки исправлены (проверка: `pytest tests/ -v` проходит).

## 1. Падающий тест: `test_classifier_marks_needs_review_for_low_confidence`

**Статус**: ✅ ИСПРАВЛЕНО

**Причина**: `ClassifierService.__init__()` требует аргумент `categories`, а тест передаёт только `llm_client`.

```python
# classifier_service.py
def __init__(self, llm_client: LLMClient, categories: List[Category]) -> None:

# test_classifier_service.py (ошибка)
service = ClassifierService(llm_client=client)  # missing categories
```

**Решение**: В тесте передать пустой список категорий: `ClassifierService(llm_client=client, categories=[])`.

---

## 2. `run_batch_classification.py` и `evaluate_on_testset.py` — не передают `categories` в ClassifierService

**Статус**: ✅ ИСПРАВЛЕНО

**Причина**: `ClassifierService` ожидает `categories` для логики multi-cluster safety (`_get_categories_for_inn`, `_apply_multi_cluster_safety`), но скрипты создают сервис без категорий:

```python
# run_batch_classification.py
service = ClassifierService(llm_client=llm_client)  # categories не переданы

# evaluate_on_testset.py
service = ClassifierService(llm_client=client)  # categories не переданы
```

**Решение**: Передавать `categories` при создании `ClassifierService`:
- `run_batch_classification.py`: уже загружает `categories` — передать в `ClassifierService(llm_client=llm_client, categories=categories)`.
- `evaluate_on_testset.py`: аналогично — `ClassifierService(llm_client=client, categories=categories)`.

---

## 3. `inn_cluster` теряется при маппинге CategoryDB → Category

**Статус**: ✅ ИСПРАВЛЕНО

**Причина**: В `category_db_to_domain()` поле `inn_cluster` жёстко задано как `None`, хотя:
- Excel и таблица `categories` содержат колонку «МНН-кластер» (маппинг в `inn_cluster`);
- `ClassifierService` и `PromptBuilder` опираются на `inn_cluster` для выбора категории.

```python
# db_io.py, category_db_to_domain
return Category(
    ...
    inn_cluster=None,  # ← всегда None, данные теряются
    ...
)
```

**Дополнительно**: В `CategoryDB` нет колонки `inn_cluster`. При загрузке xlsx `df.to_sql` создаёт колонку в таблице, но ORM-модель её не отражает. SQLAlchemy не подхватит колонку, не объявленную в модели.

**Решение**:
1. Добавить в `CategoryDB`: `inn_cluster = Column(String, nullable=True)`.
2. В `category_db_to_domain` использовать `inn_cluster=cat_db.inn_cluster` (или `getattr(cat_db, 'inn_cluster', None)` при постепенной миграции).

---

## 4. Дублирование класса `SKU` в `data_models.py`

**Статус**: ✅ ИСПРАВЛЕНО

**Причина**: В файле два определения `@dataclass class SKU`. Второе перезаписывает первое. Первое (с `name`, `external_id`) лишнее.

**Решение**: Удалить первое определение `SKU`, оставить только полное (с `manufacturer`, `alt_name`).

---

## 5. `evaluate_on_testset.py`: возможная ошибка `df.sample(n=limit)`

**Статус**: ✅ ИСПРАВЛЕНО

**Причина**: Если `limit > len(df)`, вызов `df.sample(n=limit)` приводит к `ValueError`.

**Решение**: Использовать `n=min(limit, len(df))`.

---

## 6. Неиспользуемый импорт `random` в `evaluate_on_testset.py`

**Статус**: ✅ ИСПРАВЛЕНО

**Причина**: Импорт `import random` есть, но `random` не используется (используется `df.sample(random_state=24)`).

**Решение**: Удалить `import random`.

---

## 7. Дублирование комментария в `config.py`

**Статус**: ✅ ИСПРАВЛЕНО

**Причина**: В начале файла две строки `# src/config.py`.

**Решение**: Удалить дубликат.

---

## Сводка приоритетов

| # | Ошибка                              | Приоритет | Действие                         |
|---|-------------------------------------|-----------|----------------------------------|
| 1 | Тест ClassifierService              | Высокий   | Передать `categories=[]`         |
| 2 | run_batch / evaluate без categories | Высокий   | Передать `categories` в сервис   |
| 3 | Потеря inn_cluster                  | Высокий   | Добавить колонку в ORM, исправить маппинг |
| 4 | Дублирование SKU                    | Средний   | Удалить лишнее определение       |
| 5 | df.sample при limit > len           | Средний   | `n=min(limit, len(df))`          |
| 6 | Неиспользуемый import random        | Низкий    | Удалить импорт                   |
| 7 | Дублирование комментария config     | Низкий    | Удалить дубликат                 |
