"""API key validators for LLM providers.

This module provides validators for checking API keys before usage.
Currently supports GigaChat and YandexGPT providers.

Example:
    ```python
    from orchestrator.validators import GigaChatValidator, ErrorCode
    
    validator = GigaChatValidator()
    result = await validator.validate("YOUR_KEY", scope="GIGACHAT_API_B2B")
    
    if result.valid:
        print("Valid!")
    elif result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED:
        print(f"Rate limited, retry after {result.retry_after}s")
    else:
        print(f"Error: {result.message}")
    ```
"""

from .base import BaseValidator
from .errors import ErrorCode, ValidationResult
from .gigachat import GigaChatValidator
from .yandexgpt import YandexGPTValidator

__all__ = [
    "BaseValidator",
    "GigaChatValidator",
    "YandexGPTValidator",
    "ValidationResult",
    "ErrorCode",
]
