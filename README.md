# FarmaCategorizer

Система автоматической классификации фармацевтических товаров (SKU) с использованием LLM. Проект предназначен для сопоставления аптечных наименований с иерархическим деревом категорий и извлечения структурированных данных (МНН, форма выпуска, возраст, OTC/Rx).

---

## Назначение

- **Классификация SKU** — по названию товара выбирается код категории из аптечного классификатора
- **Извлечение фарм-данных** — МНН, лекарственная форма, возрастные ограничения, статус OTC/Rx
- **Флаг needs_review** — пометка результатов для ручной проверки экспертом при низкой уверенности или неоднозначности

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Скрипты и точки входа                             │
├─────────────────────────────────────────────────────────────────────────┤
│  run_batch_classification  │  evaluate_on_testset  │  debug_one_sku      │
│  debug_sku_by_id           │  smoke_deepseek       │                     │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ClassifierService                                    │
│  - Вызов LLM                                                            │
│  - Пороги confidence (0.4 / 0.75)                                       │
│  - Multi-cluster safety (МНН-кластеры с несколькими кодами)              │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
┌───────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  ProviderLLMClient │   │    PromptBuilder    │   │      db_io          │
│  (DeepSeek API)   │   │  Системный промпт   │   │  SQLite, ProductLink │
│  Ретраи, парсинг  │   │  Few-shot примеры   │   │  CategoryDB, load    │
└───────────────────┘   └─────────────────────┘   └─────────────────────┘
```

---

## Структура проекта

```
FarmaCategorizer/
├── src/
│   ├── classifier/
│   │   ├── classifier_service.py   # Логика классификации, пороги, multi-cluster safety
│   │   └── prompt_builder.py       # Промпты, few-shot, формат JSON
│   ├── llm_client/
│   │   ├── base.py                 # LLMClient (ABC), LLMError, LLMRetryableError
│   │   └── provider_client.py      # HTTP-клиент DeepSeek API
│   ├── io/
│   │   ├── db_io.py                # ProductLink, CategoryDB, сессии, загрузка xlsx
│   │   └── file_io.py              # (заглушка)
│   ├── scripts/
│   │   ├── run_batch_classification.py  # Пакетная классификация из БД
│   │   ├── evaluate_on_testset.py       # Оценка на TestButch.xlsx
│   │   ├── debug_one_sku.py             # Отладка одного SKU
│   │   ├── debug_sku_by_id.py           # Отладка по ID ProductLink
│   │   └── migrate_product_links_columns.py
│   ├── config.py                   # LLM, Classifier, Retry
│   ├── data_models.py              # SKU, Category, ClassificationResult
│   └── smoke_deepseek.py           # Smoke-тест API
├── tests/
│   ├── test_classifier_service.py
│   ├── test_llm_client_deepseek.py
│   ├── test_llm_client_errors.py
│   ├── test_prompt_builder.py
│   └── test_smoke.py
├── pharmacy_analyzer/data/         # SQLite БД (linkages.db)
├── requirements.txt
├── pytest.ini
└── .gitignore
```

---

## Модели данных

### SKU
- `name` — название товара
- `external_id` — ID в БД (ProductLink.id)
- `manufacturer` — производитель
- `alt_name` — альтернативное название (name_asna)

### Category
- `code` — код категории
- `level`, `direction`, `need`, `group` — иерархия
- `inn_cluster` — МНН-кластер (ключевое поле для сопоставления)
- `dosage_form`, `age_segment`

### ClassificationResult
- `category_code`, `category_path`, `inn`, `dosage_form`, `age_restriction`, `otc`
- `confidence` (0..1), `needs_review`, `reason`
- `raw_llm_response` — сырой ответ LLM для отладки

---

## Конфигурация

- **`.env`** — переменные окружения (например, `DEEPSEEK_API_KEY`)
- **`config.py`** — `LLMApiConfig` (base_url, model, endpoint), `ClassifierConfig` (пороги), `RetryConfig`

---

## База данных

- **SQLite**: `pharmacy_analyzer/data/linkages.db`
- **Таблицы**:
  - `product_links` — товары из 1C/ASNA, поля классификации
  - `categories` — дерево категорий (загружается из xlsx)

---

## Запуск

### Пакетная классификация
```bash
python -m src.scripts.run_batch_classification
```

### Оценка на тестовом датасете
```bash
python -m src.scripts.evaluate_on_testset
```
(требуется `TestButch.xlsx` с колонками: Название, Производитель, Название АСНА, МНН, Код категории)

### Отладка
```bash
python -m src.scripts.debug_one_sku
python -m src.scripts.debug_sku_by_id  # id редактируется в __main__
```

### Тесты
```bash
.venv/bin/python -m pytest tests/ -v
```

---

## Зависимости

- SQLAlchemy, pandas, httpx, openpyxl
- python-dotenv
- pytest, pytest-asyncio, pytest-httpx
