"""GigaChat API key validator.

This module provides GigaChatValidator for validating GigaChat
API keys with known scope (v0.8.0 Minimal MVP).
"""

from typing import Any

import httpx

from orchestrator.providers.gigachat import GigaChatProvider

from .base import BaseValidator
from .errors import ErrorCode, ValidationResult


class GigaChatValidator(BaseValidator):
    """Validator for GigaChat API keys.
    
    This validator checks if a GigaChat authorization key is valid
    by performing OAuth2 authentication and verifying access to
    the /api/v1/models endpoint.
    
    Attributes:
        timeout: HTTP request timeout in seconds (default: 10.0)
        verify_ssl: Verify SSL certificates (default: True)
    
    Example:
        ```python
        validator = GigaChatValidator(verify_ssl=False)  # For Russian CA
        result = await validator.validate(
            api_key="YOUR_API_KEY",
            scope="GIGACHAT_API_PERS"
        )
        
        if result.valid:
            print(f"✅ Valid! Scope: {result.details.get('scope')}")
        elif result.error_code == ErrorCode.SCOPE_MISMATCH:
            print(f"❌ Scope mismatch: {result.message}")
        ```
    """

    def __init__(self, timeout: float = 10.0, verify_ssl: bool = True) -> None:
        """Initialize GigaChat validator.
        
        Args:
            timeout: HTTP request timeout in seconds (default: 10.0)
            verify_ssl: Verify SSL certificates (default: True)
                Set to False for Russian CA certificates (development only)
        """
        super().__init__(timeout=timeout)
        self.verify_ssl = verify_ssl

    async def validate(  # type: ignore[override]
        self, api_key: str, scope: str, **kwargs: Any
    ) -> ValidationResult:
        """Validate GigaChat API key.
        
        Args:
            api_key: Authorization key (credentials)
            scope: GigaChat scope (GIGACHAT_API_PERS/B2B/CORP)
            **kwargs: Additional parameters (verify_ssl override)
        
        Returns:
            ValidationResult with validation status
        
        Raises:
            ValueError: If api_key or scope is empty
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not scope:
            raise ValueError("scope cannot be empty")

        # Use verify_ssl from kwargs if provided, otherwise use instance default
        verify_ssl = kwargs.get("verify_ssl", self.verify_ssl)

        try:
            # Call GigaChatProvider.validate_api_key() classmethod
            auth_result = await GigaChatProvider.validate_api_key(
                api_key=api_key,
                scope=scope,
                verify_ssl=verify_ssl,
                timeout=self.timeout,
            )

            if not auth_result["valid"]:
                error = auth_result["error"]
                error_code = ErrorCode.PROVIDER_ERROR

                # Map error codes
                if error["http_status"] == 401:
                    error_code = ErrorCode.INVALID_API_KEY
                elif error["http_status"] == 400 and error.get("code") == 7:
                    error_code = ErrorCode.SCOPE_MISMATCH
                elif error["http_status"] == 429:
                    error_code = ErrorCode.RATE_LIMIT_EXCEEDED

                return ValidationResult(
                    valid=False,
                    error_code=error_code,
                    provider="gigachat",
                    message=error["message"],
                    details={
                        "provided_scope": scope,
                        "error_code": error.get("code"),
                    },
                    http_status=error["http_status"],
                    retry_after=30 if error["http_status"] == 429 else None,
                )

            # Success
            return ValidationResult(
                valid=True,
                error_code=ErrorCode.SUCCESS,
                provider="gigachat",
                message="API key is valid",
                details={
                    "scope": scope,
                },
                http_status=200,
            )

        except httpx.TimeoutException:
            return self._handle_timeout("gigachat")
        except Exception as exc:
            return self._handle_exception("gigachat", exc)
