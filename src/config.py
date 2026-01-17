# src/config.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class RetryConfig:
    max_retries: int = 3
    backoff_factor: float = 0.5  # секунды между повторами, можно сделать экспоненциальный рост
    retry_on_5xx: bool = True
    retry_on_429: bool = True
    retry_on_timeout: bool = True


@dataclass
class LLMApiConfig:
    base_url: str = "https://api.your-llm-provider.com/v1"
    api_key_env_var: str = "LLM_API_KEY"
    timeout_seconds: float = 30.0
    retry: RetryConfig = RetryConfig()


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


# Глобальный объект конфига, который можно импортировать
config = AppConfig()
