# src/classifier/prompt_builder.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.data_models import SKU, Category


PROMPT_SYSTEM_INSTRUCTIONS = """
Ты — эксперт по фармацевтическим препаратам и аптечным товарам.

Твоя задача:
1) По названию товара (SKU) найти информацию о препарате в открытых источниках (интернет).
2) Убедиться, что найденное описание соответствует этому SKU.
3) Извлечь:
   - МНН / действующее вещество;
   - фармакологическую группу;
   - лекарственную форму;
   - возрастные ограничения;
   - OTC или Rx (если явно указано).
4) На основании предоставленного дерева категорий выбрать ОДНУ наиболее подходящую категорию.
5) Если информации недостаточно или совпадения неоднозначные — понижать уверенность и помечать результат как needs_review = true.
6) НЕ выдумывать данные, которых нет в достоверных источниках. Лучше честно указать, что данных недостаточно.
7) Всегда возвращай ровно один JSON-объект строго заданной структуры, без текста вокруг.
8) Убедись, что confidence находится в диапазоне от 0 до 1 и согласован с твоей уверенностью.
""".strip()


PROMPT_OUTPUT_FORMAT = r"""
Верни ОДИН объект JSON СТРОГО следующей структуры (без комментариев и текста вокруг):

{
  "inn": string или null,
  "dosage_form": string или null,
  "age_restriction": string или null,
  "otc": true или false или null,
  "category_code": string или null,
  "category_path": string или null,
  "confidence": number от 0 до 1,
  "needs_review_hint": true или false,
  "reason": string
}

Никакого текста до или после JSON, никаких пояснений вне полей объекта.
""".strip()


@dataclass
class PromptBuilder:
    """
    Строитель промпта для классификации одного SKU.
    """

    def build_categories_block(self, categories: List[Category]) -> str:
        """
        Формирует текстовый блок со списком категорий.
        Позже можно будет ограничивать поддеревом.
        """
        lines = ["Дерево категорий (code — человекочитаемый путь):"]
        for cat in categories:
            path_parts = [p for p in [cat.direction, cat.need, cat.group] if p]
            path_str = " > ".join(path_parts) if path_parts else cat.code
            lines.append(f"- {cat.code}: {path_str}")
        return "\n".join(lines)

    def build_user_prompt(self, sku: SKU, categories: List[Category]) -> str:
        """
        Основной текст запроса (user message) к модели.
        """
        categories_block = self.build_categories_block(categories)

        prompt = f"""
Товар (SKU): "{sku.name}"

1) Найди информацию об этом товаре в интернете.
2) Извлеки фарм-данные (МНН, форма, возраст, OTC/Rx).
3) Выбери одну наиболее подходящую категорию из списка ниже.

{categories_block}

{PROMPT_OUTPUT_FORMAT}
""".strip()

        return prompt
