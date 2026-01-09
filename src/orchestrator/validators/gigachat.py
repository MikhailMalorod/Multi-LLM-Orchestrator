"""GigaChat API key validator.

This module provides GigaChatValidator for validating GigaChat
API keys with known scope (v0.8.0) or auto-detection (v0.8.1+).
"""

import time
from collections.abc import Callable
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
    
    Supports two modes:
    - **Known scope** (v0.8.0): Pass scope explicitly for fast validation (1 request)
    - **Auto-detection** (v0.8.1+): Omit scope to automatically detect it (up to 3 requests)
    
    Attributes:
        timeout: HTTP request timeout in seconds (default: 10.0)
        verify_ssl: Verify SSL certificates (default: True)
    
    Example:
        ```python
        validator = GigaChatValidator(verify_ssl=False)  # For Russian CA
        
        # Known scope (fast, 1 request)
        result = await validator.validate(
            api_key="YOUR_API_KEY",
            scope="GIGACHAT_API_PERS"
        )
        
        # Auto-detection (slower, up to 3 requests)
        result = await validator.validate(api_key="YOUR_API_KEY")
        
        if result.valid:
            detected_scope = result.details.get("detected_scope") or result.details.get("scope")
            print(f"✅ Valid! Scope: {detected_scope}")
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

    async def validate(
        self,
        api_key: str,
        scope: str | None = None,
        on_scope_attempt: Callable[[str, int, int], None] | None = None,
        **kwargs: Any,
    ) -> ValidationResult:
        """Validate GigaChat API key.
        
        Args:
            api_key: Authorization key (credentials)
            scope: GigaChat scope (GIGACHAT_API_PERS/B2B/CORP).
                If None, auto-detects scope by trying all variants (v0.8.1+).
            on_scope_attempt: Optional callback for progress tracking during auto-detection.
                Called before each scope validation attempt.
                Signature: (scope: str, current: int, total: int) -> None
                Example: on_scope_attempt("GIGACHAT_API_PERS", 1, 3)
                Note: Only called during auto-detection (when scope is None).
            **kwargs: Additional parameters (verify_ssl override)
        
        Returns:
            ValidationResult with validation status.
            If scope is auto-detected, result.details contains:
            - "detected_scope": The detected scope
            - "auto_detection_used": True
            - "attempts_count": Number of scopes tried
            - "total_time_ms": Time taken in milliseconds
            - "attempted_scopes": List of scopes attempted
        
        Raises:
            ValueError: If api_key is empty
        
        Example:
            ```python
            validator = GigaChatValidator()
            
            # Known scope (fast, 1 request)
            result = await validator.validate(
                api_key="YOUR_KEY",
                scope="GIGACHAT_API_PERS"
            )
            
            # Auto-detection with progress callback
            def show_progress(scope: str, current: int, total: int):
                print(f"Checking {scope} ({current}/{total})...")
            
            result = await validator.validate(
                api_key="YOUR_KEY",
                on_scope_attempt=show_progress
            )
            ```
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")

        # If scope is provided (not None), use fast validation (v0.8.0 behavior)
        if scope is not None:
            return await self._validate_with_known_scope(api_key, scope, **kwargs)

        # Otherwise, use auto-detection (v0.8.1+)
        return await self._validate_with_auto_detect(
            api_key, on_scope_attempt, **kwargs
        )

    async def _validate_with_known_scope(
        self, api_key: str, scope: str, **kwargs: Any
    ) -> ValidationResult:
        """Validate GigaChat API key with known scope (v0.8.0 behavior).
        
        Args:
            api_key: Authorization key (credentials)
            scope: GigaChat scope (GIGACHAT_API_PERS/B2B/CORP)
            **kwargs: Additional parameters (verify_ssl override)
        
        Returns:
            ValidationResult with validation status
        
        Raises:
            ValueError: If scope is empty
        """
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
                        "auto_detection_used": False,
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
                    "auto_detection_used": False,
                },
                http_status=200,
            )

        except httpx.TimeoutException:
            return self._handle_timeout("gigachat")
        except Exception as exc:
            return self._handle_exception("gigachat", exc)

    async def _validate_with_auto_detect(
        self,
        api_key: str,
        on_scope_attempt: Callable[[str, int, int], None] | None,
        **kwargs: Any,
    ) -> ValidationResult:
        """Auto-detect GigaChat scope by trying all variants (v0.8.1+).
        
        This method tries scopes in order: PERS → B2B → CORP.
        Stops immediately on errors other than scope mismatch (401, 429, timeout, 500+).
        
        Args:
            api_key: Authorization key
            on_scope_attempt: Optional callback for progress tracking.
                Called before each scope validation attempt.
            **kwargs: Additional parameters (verify_ssl override)
        
        Returns:
            ValidationResult with detected_scope in details if successful,
            or error details if all scopes failed or auto-detection stopped.
        """
        scopes_to_try = [
            "GIGACHAT_API_PERS",
            "GIGACHAT_API_B2B",
            "GIGACHAT_API_CORP",
        ]

        verify_ssl = kwargs.get("verify_ssl", self.verify_ssl)
        start_time = time.time()
        attempted_scopes: list[str] = []
        last_error: dict[str, Any] | None = None

        for idx, scope in enumerate(scopes_to_try, 1):
            # Notify callback before attempting this scope
            if on_scope_attempt:
                on_scope_attempt(scope, idx, len(scopes_to_try))

            attempted_scopes.append(scope)

            try:
                # Try validation with current scope
                auth_result = await GigaChatProvider.validate_api_key(
                    api_key=api_key,
                    scope=scope,
                    verify_ssl=verify_ssl,
                    timeout=self.timeout,
                )

                if auth_result["valid"]:
                    # SUCCESS: scope detected
                    end_time = time.time()
                    total_time_ms = int((end_time - start_time) * 1000)

                    return ValidationResult(
                        valid=True,
                        error_code=ErrorCode.SUCCESS,
                        provider="gigachat",
                        message=f"API key is valid (auto-detected scope: {scope})",
                        details={
                            "scope": scope,
                            "detected_scope": scope,
                            "auto_detection_used": True,
                            "attempts_count": idx,
                            "total_time_ms": total_time_ms,
                            "attempted_scopes": attempted_scopes,
                        },
                        http_status=200,
                    )

                # Check error type
                error = auth_result["error"]

                # If scope mismatch (400, code:7) → try next scope
                if error["http_status"] == 400 and error.get("code") == 7:
                    last_error = error
                    continue  # Try next scope

                # Any other error (401, 429, 500, timeout) → stop immediately
                end_time = time.time()
                total_time_ms = int((end_time - start_time) * 1000)

                error_code = ErrorCode.PROVIDER_ERROR
                stopped_reason = "provider_error"

                if error["http_status"] == 401:
                    error_code = ErrorCode.INVALID_API_KEY
                    stopped_reason = "invalid_api_key"
                elif error["http_status"] == 429:
                    error_code = ErrorCode.RATE_LIMIT_EXCEEDED
                    stopped_reason = "rate_limit_exceeded"

                return ValidationResult(
                    valid=False,
                    error_code=error_code,
                    provider="gigachat",
                    message=error["message"],
                    details={
                        "auto_detection_used": True,
                        "auto_detection_stopped": True,
                        "stopped_reason": stopped_reason,
                        "attempts_count": idx,
                        "total_time_ms": total_time_ms,
                        "attempted_scopes": attempted_scopes,
                    },
                    http_status=error["http_status"],
                    retry_after=30 if error["http_status"] == 429 else None,
                )

            except httpx.TimeoutException:
                # Timeout → stop immediately
                end_time = time.time()
                total_time_ms = int((end_time - start_time) * 1000)

                result = self._handle_timeout("gigachat")
                result.details = {
                    "auto_detection_used": True,
                    "auto_detection_stopped": True,
                    "stopped_reason": "timeout",
                    "attempts_count": idx,
                    "total_time_ms": total_time_ms,
                    "attempted_scopes": attempted_scopes,
                }
                return result

            except Exception as exc:
                # Unexpected error → stop immediately
                end_time = time.time()
                total_time_ms = int((end_time - start_time) * 1000)

                result = self._handle_exception("gigachat", exc)
                result.details = {
                    "auto_detection_used": True,
                    "auto_detection_stopped": True,
                    "stopped_reason": "provider_error",
                    "attempts_count": idx,
                    "total_time_ms": total_time_ms,
                    "attempted_scopes": attempted_scopes,
                }
                return result

        # All scopes exhausted → SCOPE_MISMATCH
        end_time = time.time()
        total_time_ms = int((end_time - start_time) * 1000)

        return ValidationResult(
            valid=False,
            error_code=ErrorCode.SCOPE_MISMATCH,
            provider="gigachat",
            message="Could not detect valid scope: all variants (PERS/B2B/CORP) failed",
            details={
                "auto_detection_used": True,
                "auto_detection_stopped": True,
                "stopped_reason": "scope_mismatch",
                "attempts_count": len(scopes_to_try),
                "total_time_ms": total_time_ms,
                "attempted_scopes": attempted_scopes,
                "last_error": last_error,
            },
            http_status=400,
        )
