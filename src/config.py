# src/config.py
from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv

# Загружаем .env
load_dotenv()


@dataclass
class RetryConfig:
    max_retries: int = 3
    backoff_factor: float = 0.5  # секунды между повторами
    retry_on_5xx: bool = True
    retry_on_429: bool = True
    retry_on_timeout: bool = True


@dataclass
class LLMApiConfig:
    """
    Конфиг LLM-провайдера.
    Сейчас настроен на DeepSeek, но поле provider оставлено для будущих вариантов.
    """
    provider: str = "deepseek"  # "deepseek" | "openai" | "anthropic" ...
    base_url: str = "https://api.deepseek.com/v1"
    api_key_env_var: str = "DEEPSEEK_API_KEY"
    timeout_seconds: float = 30.0
    retry: RetryConfig = RetryConfig()
    model: str = "deepseek-chat"
    endpoint: str = "/chat/completions"


@dataclass
class ClassifierConfig:
    # Порог уверенности, ниже — needs_review = True
    confidence_threshold: float = 0.75
    # Порог, ниже которого вообще не присваиваем категорию
    hard_reject_threshold: float = 0.4


@dataclass
class AppConfig:
    llm: LLMApiConfig = LLMApiConfig()
    classifier: ClassifierConfig = ClassifierConfig()


# Глобальный объект конфига, который можно импортировать как `from src.config import config`
config = AppConfig()
