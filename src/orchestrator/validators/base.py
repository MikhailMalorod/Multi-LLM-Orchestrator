"""Base validator interface for API key validators.

This module provides the abstract base class that all API key
validators must implement.
"""

from abc import ABC, abstractmethod
from typing import Any

from .errors import ErrorCode, ValidationResult


class BaseValidator(ABC):
    """Base class for API key validators.
    
    This abstract base class defines the interface that all
    provider-specific validators must implement. It provides
    helper methods for common error handling scenarios.
    
    Attributes:
        timeout: HTTP request timeout in seconds (default: 10.0)
    
    Example:
        ```python
        class MyValidator(BaseValidator):
            async def validate(self, api_key: str, **kwargs) -> ValidationResult:
                # Implementation here
                pass
        ```
    """

    def __init__(self, timeout: float = 10.0) -> None:
        """Initialize validator.
        
        Args:
            timeout: HTTP request timeout in seconds (default: 10.0)
        """
        self.timeout = timeout

    @abstractmethod
    async def validate(self, api_key: str, **kwargs: Any) -> ValidationResult:
        """Validate API key.
        
        Args:
            api_key: API key to validate
            **kwargs: Provider-specific parameters
        
        Returns:
            ValidationResult with validation status and details
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        pass

    def _handle_timeout(self, provider: str) -> ValidationResult:
        """Handle httpx.TimeoutException.
        
        Args:
            provider: Provider name (e.g., "gigachat", "yandexgpt")
        
        Returns:
            ValidationResult with NETWORK_TIMEOUT error code
        """
        return ValidationResult(
            valid=False,
            error_code=ErrorCode.NETWORK_TIMEOUT,
            provider=provider,
            message=f"{provider} API validation timeout",
            http_status=504,
        )

    def _handle_exception(self, provider: str, exc: Exception) -> ValidationResult:
        """Handle unexpected exceptions.
        
        Args:
            provider: Provider name (e.g., "gigachat", "yandexgpt")
            exc: Exception that occurred
        
        Returns:
            ValidationResult with VALIDATION_ERROR error code
        """
        return ValidationResult(
            valid=False,
            error_code=ErrorCode.VALIDATION_ERROR,
            provider=provider,
            message=str(exc),
            http_status=500,
        )
