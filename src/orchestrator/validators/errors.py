"""Error types and validation results for API key validators.

This module defines the error codes and result structures used by
all API key validators in the Multi-LLM Orchestrator.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Validation error codes.
    
    These codes represent different types of validation failures
    that can occur when validating API keys for LLM providers.
    """
    # Success
    SUCCESS = "success"

    # Client errors (4xx)
    INVALID_API_KEY = "invalid_api_key"              # 401
    SCOPE_MISMATCH = "scope_mismatch"                # 400 (GigaChat code:7)
    PERMISSION_DENIED = "permission_denied"          # 403 (YandexGPT)
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"      # 429

    # Network errors (5xx)
    NETWORK_TIMEOUT = "network_timeout"              # 504
    PROVIDER_ERROR = "provider_error"                # 500

    # Internal errors
    VALIDATION_ERROR = "validation_error"            # Unexpected error


@dataclass
class ValidationResult:
    """Result of API key validation.
    
    This dataclass represents the result of validating an API key
    for a specific LLM provider. It includes the validation status,
    error code, provider name, and optional details.
    
    Attributes:
        valid: True if key is valid, False otherwise
        error_code: Error code (always present, even for success)
        provider: Provider name ("gigachat" or "yandexgpt")
        message: Human-readable English message (for logs)
        details: Optional dict with provider-specific data
        http_status: Original HTTP status code (if applicable)
        retry_after: Seconds to wait before retry (for rate limits)
    
    Example:
        ```python
        # Success case
        result = ValidationResult(
            valid=True,
            error_code=ErrorCode.SUCCESS,
            provider="gigachat",
            message="API key is valid",
            details={"scope": "GIGACHAT_API_PERS"},
            http_status=200,
        )
        
        # Error case
        result = ValidationResult(
            valid=False,
            error_code=ErrorCode.SCOPE_MISMATCH,
            provider="gigachat",
            message="Scope mismatch: provided 'GIGACHAT_API_PERS' but key requires different scope",
            details={"provided_scope": "GIGACHAT_API_PERS"},
            http_status=400,
        )
        ```
    """
    valid: bool
    error_code: ErrorCode
    provider: str
    message: str
    details: dict[str, Any] | None = None
    http_status: int | None = None
    retry_after: int | None = None
