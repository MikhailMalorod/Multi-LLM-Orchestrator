# ДЕТАЛЬНЫЙ ПЛАН РЕАЛИЗАЦИИ: API Key Validators Module (v0.8.0)

**Версия**: 0.8.0 Minimal MVP  
**Дата**: 2026-01-17  
**Статус**: Готов к реализации

---

## 📋 ОБЗОР

Реализуем модуль `src/orchestrator/validators/` для валидации API-ключей GigaChat и YandexGPT.

**Цель**: Minimal MVP с базовой функциональностью, без scope auto-detection.

**Timeline**: 7 дней (Day 1-2: errors + base, Day 3-4: validators, Day 5-6: tests, Day 7: docs)

---

## 🎯 ПОСЛЕДОВАТЕЛЬНОСТЬ РЕАЛИЗАЦИИ

### Phase 1: Базовая инфраструктура (Day 1-2)
1. ✅ Создать `src/orchestrator/validators/` директорию
2. ✅ Реализовать `errors.py` (ErrorCode, ValidationResult)
3. ✅ Реализовать `base.py` (BaseValidator ABC)
4. ✅ Реализовать `__init__.py` (public API exports)

### Phase 2: GigaChat валидатор (Day 3)
5. ✅ Рефакторинг `GigaChatProvider` (публичный метод)
6. ✅ Реализовать `gigachat.py` (GigaChatValidator)

### Phase 3: YandexGPT валидатор (Day 4)
7. ✅ Реализовать `yandexgpt.py` (YandexGPTValidator)

### Phase 4: Тесты (Day 5-6)
8. ✅ Создать `tests/validators/` директорию
9. ✅ Тесты для `errors.py` и `base.py`
10. ✅ Тесты для `GigaChatValidator`
11. ✅ Тесты для `YandexGPTValidator`
12. ✅ Edge cases и error scenarios

### Phase 5: Документация (Day 7)
13. ✅ Обновить `README.md` (раздел "API Key Validation")
14. ✅ Создать `examples/validation_demo.py`
15. ✅ Обновить `CHANGELOG.md`
16. ✅ Проверить coverage (цель: 80%+)

---

## 📁 СТРУКТУРА ФАЙЛОВ

```
src/orchestrator/
├── validators/                    # ← NEW MODULE
│   ├── __init__.py               # Public API exports
│   ├── base.py                   # BaseValidator (ABC)
│   ├── errors.py                 # ValidationResult, ErrorCode
│   ├── gigachat.py               # GigaChatValidator
│   └── yandexgpt.py              # YandexGPTValidator
│
├── providers/                     # EXISTING (минимальный рефакторинг)
│   └── gigachat.py               # Добавить публичный метод
│
tests/
├── validators/                    # ← NEW TESTS
│   ├── __init__.py
│   ├── test_base.py
│   ├── test_errors.py
│   ├── test_gigachat_validator.py
│   └── test_yandexgpt_validator.py
```

---

## 🔧 ДЕТАЛЬНЫЕ ИНСТРУКЦИИ

### STEP 1: Создать директорию `validators/`

```bash
mkdir -p src/orchestrator/validators
mkdir -p tests/validators
```

---

### STEP 2: Реализовать `errors.py`

**Файл**: `src/orchestrator/validators/errors.py`

**Содержимое**:

```python
"""Error types and validation results for API key validators.

This module defines the error codes and result structures used by
all API key validators in the Multi-LLM Orchestrator.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    details: Optional[dict] = None
    http_status: Optional[int] = None
    retry_after: Optional[int] = None
```

**Проверка**:
- ✅ Все ErrorCode значения определены
- ✅ ValidationResult dataclass с правильными типами
- ✅ Docstrings с примерами

---

### STEP 3: Реализовать `base.py`

**Файл**: `src/orchestrator/validators/base.py`

**Содержимое**:

```python
"""Base validator interface for API key validators.

This module provides the abstract base class that all API key
validators must implement.
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx

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
    async def validate(self, api_key: str, **kwargs) -> ValidationResult:
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
```

**Проверка**:
- ✅ BaseValidator - ABC с abstractmethod validate()
- ✅ Helper методы _handle_timeout() и _handle_exception()
- ✅ Правильные импорты

---

### STEP 4: Рефакторинг `GigaChatProvider`

**Файл**: `src/orchestrator/providers/gigachat.py`

**Изменения**:

1. **Переименовать `_ensure_access_token()` → `get_access_token()`** (убрать `_`)

```python
# БЫЛО:
async def _ensure_access_token(self) -> str:

# СТАЛО:
async def get_access_token(self) -> str:
    """Get or refresh OAuth2 access token.
    
    This method implements thread-safe OAuth2 token management:
    1. Checks if current token is valid (with 60s buffer before expiration)
    2. If token is missing or expired, requests a new one via OAuth2 endpoint
    3. Uses async lock to prevent concurrent token refresh requests
    
    Returns:
        Valid access token string
    
    Raises:
        AuthenticationError: If authorization key is invalid (401 response)
        ProviderError: If OAuth2 request fails for other reasons
    
    Example:
        ```python
        token = await provider.get_access_token()
        ```
    """
    # Существующий код остается без изменений
```

2. **Обновить все вызовы `_ensure_access_token()` → `get_access_token()`** в том же файле:
   - В методе `generate()` (строка ~309)
   - В методе `generate_stream()` (строка ~599)
   - В методе `health_check()` (строка ~423)

3. **Добавить classmethod `validate_api_key()`**:

```python
@classmethod
async def validate_api_key(
    cls,
    api_key: str,
    scope: str = "GIGACHAT_API_PERS",
    verify_ssl: bool = True,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Validate GigaChat API key (class method for validators).
    
    This method performs OAuth2 authentication and validates
    the API key by checking access to the /api/v1/models endpoint.
    
    Args:
        api_key: Authorization key (credentials)
        scope: GigaChat scope (GIGACHAT_API_PERS/B2B/CORP)
        verify_ssl: Verify SSL certificates (default: True)
        timeout: Request timeout in seconds (default: 10.0)
    
    Returns:
        dict with keys:
            - "valid": bool - True if key is valid
            - "access_token": str - OAuth2 access token (if valid)
            - "error": Optional[dict] - Error details (if invalid)
                - "message": str - Error message
                - "http_status": int - HTTP status code
                - "code": Optional[int] - GigaChat error code
    
    Raises:
        ValueError: If api_key or scope is empty
        httpx.TimeoutException: If request times out
    """
    if not api_key:
        raise ValueError("api_key cannot be empty")
    if not scope:
        raise ValueError("scope cannot be empty")
    
    # Step 1: Get OAuth2 access token
    oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    async with httpx.AsyncClient(timeout=timeout, verify=verify_ssl) as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"scope": scope}
        
        try:
            response = await client.post(oauth_url, headers=headers, data=data)
            
            if response.status_code == 401:
                return {
                    "valid": False,
                    "access_token": None,
                    "error": {
                        "message": "Invalid authorization key",
                        "http_status": 401,
                        "code": None,
                    },
                }
            
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data["access_token"]
            
            # Step 2: Validate access to /api/v1/models
            models_url = "https://gigachat.devices.sberbank.ru/api/v1/models"
            models_response = await client.get(
                models_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if models_response.status_code == 200:
                return {
                    "valid": True,
                    "access_token": access_token,
                    "error": None,
                }
            
            # Handle models endpoint errors
            if models_response.status_code == 400:
                error_data = models_response.json()
                if error_data.get("code") == 7:  # scope mismatch
                    return {
                        "valid": False,
                        "access_token": None,
                        "error": {
                            "message": f"Scope mismatch: provided '{scope}' but key requires different scope",
                            "http_status": 400,
                            "code": 7,
                        },
                    }
            
            if models_response.status_code == 429:
                return {
                    "valid": False,
                    "access_token": None,
                    "error": {
                        "message": "Rate limit exceeded",
                        "http_status": 429,
                        "code": None,
                    },
                }
            
            # Other errors
            return {
                "valid": False,
                "access_token": None,
                "error": {
                    "message": models_response.text or f"HTTP {models_response.status_code}",
                    "http_status": models_response.status_code,
                    "code": None,
                },
            }
            
        except httpx.TimeoutException:
            raise
        except Exception as e:
            return {
                "valid": False,
                "access_token": None,
                "error": {
                    "message": str(e),
                    "http_status": 500,
                    "code": None,
                },
            }
```

**Проверка**:
- ✅ `_ensure_access_token()` переименован в `get_access_token()`
- ✅ Все вызовы обновлены
- ✅ Добавлен `validate_api_key()` classmethod
- ✅ Существующие тесты проходят (не сломали backward compatibility)

---

### STEP 5: Реализовать `gigachat.py`

**Файл**: `src/orchestrator/validators/gigachat.py`

**Содержимое**:

```python
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
    
    async def validate(
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
```

**Проверка**:
- ✅ Импортирует GigaChatProvider.validate_api_key()
- ✅ Обрабатывает все error codes
- ✅ Возвращает правильный ValidationResult
- ✅ Edge cases (пустые параметры)

---

### STEP 6: Реализовать `yandexgpt.py`

**Файл**: `src/orchestrator/validators/yandexgpt.py`

**Содержимое**:

```python
"""YandexGPT API key validator.

This module provides YandexGPTValidator for validating YandexGPT
IAM tokens and folder_id permissions.
"""

from typing import Any, Optional

import httpx

from .base import BaseValidator
from .errors import ErrorCode, ValidationResult


# gRPC error code mapping
GRPC_CODE_TO_ERROR: dict[int, ErrorCode] = {
    16: ErrorCode.INVALID_API_KEY,       # UNAUTHENTICATED
    7: ErrorCode.PERMISSION_DENIED,      # PERMISSION_DENIED
    8: ErrorCode.RATE_LIMIT_EXCEEDED,    # RESOURCE_EXHAUSTED
    13: ErrorCode.PROVIDER_ERROR,        # INTERNAL
}


class YandexGPTValidator(BaseValidator):
    """Validator for YandexGPT IAM tokens and folder_id.
    
    This validator checks if a YandexGPT IAM token is valid and
    has access to the specified folder_id by making a minimal
    request to the completion endpoint.
    
    Attributes:
        timeout: HTTP request timeout in seconds (default: 10.0)
    
    Example:
        ```python
        validator = YandexGPTValidator()
        result = await validator.validate(
            api_key="YOUR_IAM_TOKEN",
            folder_id="b1g..."
        )
        
        if result.valid:
            print("✅ Valid!")
        elif result.error_code == ErrorCode.PERMISSION_DENIED:
            print(f"❌ No access to folder_id: {result.details.get('folder_id')}")
            print(f"Request ID: {result.details.get('request_id')}")
        ```
    """
    
    DEFAULT_BASE_URL: str = "https://llm.api.cloud.yandex.net"
    API_ENDPOINT: str = "/foundationModels/v1/completion"
    
    def __init__(self, timeout: float = 10.0) -> None:
        """Initialize YandexGPT validator.
        
        Args:
            timeout: HTTP request timeout in seconds (default: 10.0)
        """
        super().__init__(timeout=timeout)
    
    def _extract_request_id(self, response: httpx.Response) -> Optional[str]:
        """Extract request_id from response (headers or error body).
        
        Args:
            response: HTTPX response object
        
        Returns:
            Request ID string if found, None otherwise
        """
        # Try headers first
        request_id = response.headers.get("x-request-id")
        if request_id:
            return request_id
        
        # Try error body (google.rpc.RequestInfo)
        try:
            error_data = response.json().get("error", {})
            details = error_data.get("details", [])
            for detail in details:
                if detail.get("@type") == "type.googleapis.com/google.rpc.RequestInfo":
                    return detail.get("requestId")
        except Exception:
            pass
        
        return None
    
    def _parse_yandex_error(
        self, response: httpx.Response, folder_id: str
    ) -> ValidationResult:
        """Parse YandexGPT error response.
        
        Args:
            response: HTTPX response object with error
            folder_id: Folder ID that was validated
        
        Returns:
            ValidationResult with error details
        """
        try:
            error_data = response.json().get("error", {})
            grpc_code = error_data.get("grpcCode")
            message = error_data.get("message", "Unknown error")
            
            error_code = GRPC_CODE_TO_ERROR.get(
                grpc_code, ErrorCode.PROVIDER_ERROR
            )
            
            request_id = self._extract_request_id(response)
            
            return ValidationResult(
                valid=False,
                error_code=error_code,
                provider="yandexgpt",
                message=message,
                details={
                    "folder_id": folder_id,
                    "grpc_code": grpc_code,
                    "request_id": request_id,
                },
                http_status=response.status_code,
                retry_after=10 if error_code == ErrorCode.RATE_LIMIT_EXCEEDED else None,
            )
        except Exception as e:
            return self._handle_exception("yandexgpt", e)
    
    async def validate(
        self, api_key: str, folder_id: str, **kwargs: Any
    ) -> ValidationResult:
        """Validate YandexGPT IAM token and folder_id.
        
        Args:
            api_key: IAM token (credentials)
            folder_id: Yandex Cloud folder ID
            **kwargs: Additional parameters (unused for now)
        
        Returns:
            ValidationResult with validation status
        
        Raises:
            ValueError: If api_key or folder_id is empty
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not folder_id:
            raise ValueError("folder_id cannot be empty")
        
        # Prepare minimal request body (maxTokens: 1, yandexgpt-lite/latest)
        request_body = {
            "modelUri": f"gpt://{folder_id}/yandexgpt-lite/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.1,
                "maxTokens": 1,
            },
            "messages": [
                {
                    "role": "user",
                    "text": "test",
                }
            ],
        }
        
        url = f"{self.DEFAULT_BASE_URL}{self.API_ENDPOINT}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=request_body)
                
                if response.status_code == 200:
                    return ValidationResult(
                        valid=True,
                        error_code=ErrorCode.SUCCESS,
                        provider="yandexgpt",
                        message="API key is valid",
                        details={
                            "folder_id": folder_id,
                        },
                        http_status=200,
                    )
                
                # Parse error
                return self._parse_yandex_error(response, folder_id)
                
        except httpx.TimeoutException:
            return self._handle_timeout("yandexgpt")
        except Exception as exc:
            return self._handle_exception("yandexgpt", exc)
```

**Проверка**:
- ✅ Правильный request body (maxTokens: 1, yandexgpt-lite/latest)
- ✅ Извлечение request_id из headers и error body
- ✅ Маппинг gRPC codes на ErrorCode
- ✅ Edge cases (пустые параметры)

---

### STEP 7: Реализовать `__init__.py`

**Файл**: `src/orchestrator/validators/__init__.py`

**Содержимое**:

```python
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
```

**Проверка**:
- ✅ Все экспорты правильные
- ✅ Docstring с примером

---

### STEP 8: Тесты для `errors.py`

**Файл**: `tests/validators/test_errors.py`

**Содержимое**:

```python
"""Tests for validation error types."""

import pytest

from orchestrator.validators.errors import ErrorCode, ValidationResult


class TestErrorCode:
    """Test ErrorCode enum."""
    
    def test_error_code_values(self):
        """Test that all error codes have correct string values."""
        assert ErrorCode.SUCCESS == "success"
        assert ErrorCode.INVALID_API_KEY == "invalid_api_key"
        assert ErrorCode.SCOPE_MISMATCH == "scope_mismatch"
        assert ErrorCode.PERMISSION_DENIED == "permission_denied"
        assert ErrorCode.RATE_LIMIT_EXCEEDED == "rate_limit_exceeded"
        assert ErrorCode.NETWORK_TIMEOUT == "network_timeout"
        assert ErrorCode.PROVIDER_ERROR == "provider_error"
        assert ErrorCode.VALIDATION_ERROR == "validation_error"


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_success_result(self):
        """Test success validation result."""
        result = ValidationResult(
            valid=True,
            error_code=ErrorCode.SUCCESS,
            provider="gigachat",
            message="API key is valid",
            details={"scope": "GIGACHAT_API_PERS"},
            http_status=200,
        )
        
        assert result.valid is True
        assert result.error_code == ErrorCode.SUCCESS
        assert result.provider == "gigachat"
        assert result.message == "API key is valid"
        assert result.details == {"scope": "GIGACHAT_API_PERS"}
        assert result.http_status == 200
        assert result.retry_after is None
    
    def test_error_result(self):
        """Test error validation result."""
        result = ValidationResult(
            valid=False,
            error_code=ErrorCode.SCOPE_MISMATCH,
            provider="gigachat",
            message="Scope mismatch",
            details={"provided_scope": "GIGACHAT_API_PERS"},
            http_status=400,
        )
        
        assert result.valid is False
        assert result.error_code == ErrorCode.SCOPE_MISMATCH
        assert result.http_status == 400
    
    def test_rate_limit_result(self):
        """Test rate limit result with retry_after."""
        result = ValidationResult(
            valid=False,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            provider="gigachat",
            message="Rate limit exceeded",
            http_status=429,
            retry_after=30,
        )
        
        assert result.retry_after == 30
```

---

### STEP 9: Тесты для `base.py`

**Файл**: `tests/validators/test_base.py`

**Содержимое**:

```python
"""Tests for BaseValidator."""

import pytest

from orchestrator.validators.base import BaseValidator
from orchestrator.validators.errors import ErrorCode


class ConcreteValidator(BaseValidator):
    """Concrete validator for testing."""
    
    async def validate(self, api_key: str, **kwargs):
        from orchestrator.validators.errors import ValidationResult, ErrorCode
        return ValidationResult(
            valid=True,
            error_code=ErrorCode.SUCCESS,
            provider="test",
            message="Test",
        )


class TestBaseValidator:
    """Test BaseValidator functionality."""
    
    def test_init(self):
        """Test validator initialization."""
        validator = ConcreteValidator(timeout=5.0)
        assert validator.timeout == 5.0
    
    def test_default_timeout(self):
        """Test default timeout."""
        validator = ConcreteValidator()
        assert validator.timeout == 10.0
    
    def test_handle_timeout(self):
        """Test _handle_timeout helper."""
        validator = ConcreteValidator()
        result = validator._handle_timeout("test_provider")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.NETWORK_TIMEOUT
        assert result.provider == "test_provider"
        assert result.http_status == 504
    
    def test_handle_exception(self):
        """Test _handle_exception helper."""
        validator = ConcreteValidator()
        exc = ValueError("Test error")
        result = validator._handle_exception("test_provider", exc)
        
        assert result.valid is False
        assert result.error_code == ErrorCode.VALIDATION_ERROR
        assert result.provider == "test_provider"
        assert result.message == "Test error"
        assert result.http_status == 500
    
    @pytest.mark.asyncio
    async def test_validate_abstract(self):
        """Test that validate() is abstract."""
        validator = ConcreteValidator()
        result = await validator.validate("test_key")
        assert result.valid is True
```

---

### STEP 10: Тесты для `GigaChatValidator`

**Файл**: `tests/validators/test_gigachat_validator.py`

**Содержимое** (основные тесты):

```python
"""Tests for GigaChatValidator."""

import pytest
import pytest_httpx

from orchestrator.validators import GigaChatValidator, ErrorCode


class TestGigaChatValidator:
    """Test GigaChatValidator functionality."""
    
    @pytest.mark.asyncio
    async def test_valid_key(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test valid GigaChat key."""
        # Mock OAuth2 response
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token", "expires_at": 1234567890},
        )
        
        # Mock /models response
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=200,
            json={"data": [{"id": "GigaChat"}]},
        )
        
        validator = GigaChatValidator()
        result = await validator.validate("test_key", scope="GIGACHAT_API_PERS")
        
        assert result.valid is True
        assert result.error_code == ErrorCode.SUCCESS
        assert result.provider == "gigachat"
        assert result.http_status == 200
        assert result.details["scope"] == "GIGACHAT_API_PERS"
    
    @pytest.mark.asyncio
    async def test_invalid_key(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test invalid GigaChat key (401)."""
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=401,
        )
        
        validator = GigaChatValidator()
        result = await validator.validate("invalid_key", scope="GIGACHAT_API_PERS")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.INVALID_API_KEY
        assert result.http_status == 401
    
    @pytest.mark.asyncio
    async def test_scope_mismatch(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test scope mismatch (400, code:7)."""
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token", "expires_at": 1234567890},
        )
        
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )
        
        validator = GigaChatValidator()
        result = await validator.validate("test_key", scope="GIGACHAT_API_PERS")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.SCOPE_MISMATCH
        assert result.http_status == 400
        assert result.details["provided_scope"] == "GIGACHAT_API_PERS"
    
    @pytest.mark.asyncio
    async def test_rate_limit(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test rate limit (429)."""
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token", "expires_at": 1234567890},
        )
        
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=429,
        )
        
        validator = GigaChatValidator()
        result = await validator.validate("test_key", scope="GIGACHAT_API_PERS")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert result.retry_after == 30
    
    @pytest.mark.asyncio
    async def test_timeout(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test timeout handling."""
        httpx_mock.add_exception(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            exception=httpx.TimeoutException("Timeout"),
        )
        
        validator = GigaChatValidator()
        result = await validator.validate("test_key", scope="GIGACHAT_API_PERS")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.NETWORK_TIMEOUT
        assert result.http_status == 504
    
    @pytest.mark.asyncio
    async def test_empty_api_key(self):
        """Test empty api_key raises ValueError."""
        validator = GigaChatValidator()
        with pytest.raises(ValueError, match="api_key cannot be empty"):
            await validator.validate("", scope="GIGACHAT_API_PERS")
    
    @pytest.mark.asyncio
    async def test_empty_scope(self):
        """Test empty scope raises ValueError."""
        validator = GigaChatValidator()
        with pytest.raises(ValueError, match="scope cannot be empty"):
            await validator.validate("test_key", scope="")
```

**Добавить еще тесты**:
- Server error (500+)
- verify_ssl parameter
- Custom timeout

---

### STEP 11: Тесты для `YandexGPTValidator`

**Файл**: `tests/validators/test_yandexgpt_validator.py`

**Содержимое** (основные тесты):

```python
"""Tests for YandexGPTValidator."""

import pytest
import pytest_httpx
import httpx

from orchestrator.validators import YandexGPTValidator, ErrorCode


class TestYandexGPTValidator:
    """Test YandexGPTValidator functionality."""
    
    @pytest.mark.asyncio
    async def test_valid_key(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test valid YandexGPT key."""
        httpx_mock.add_response(
            method="POST",
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            status_code=200,
            json={
                "result": {
                    "alternatives": [{"message": {"text": "test"}}]
                }
            },
        )
        
        validator = YandexGPTValidator()
        result = await validator.validate("test_token", folder_id="b1g123")
        
        assert result.valid is True
        assert result.error_code == ErrorCode.SUCCESS
        assert result.provider == "yandexgpt"
        assert result.http_status == 200
        assert result.details["folder_id"] == "b1g123"
    
    @pytest.mark.asyncio
    async def test_invalid_key(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test invalid IAM token (401, grpc_code:16)."""
        httpx_mock.add_response(
            method="POST",
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            status_code=401,
            json={
                "error": {
                    "grpcCode": 16,
                    "httpCode": 401,
                    "message": "UNAUTHENTICATED",
                }
            },
        )
        
        validator = YandexGPTValidator()
        result = await validator.validate("invalid_token", folder_id="b1g123")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.INVALID_API_KEY
        assert result.http_status == 401
        assert result.details["grpc_code"] == 16
    
    @pytest.mark.asyncio
    async def test_permission_denied(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test permission denied (403, grpc_code:7)."""
        httpx_mock.add_response(
            method="POST",
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            status_code=403,
            json={
                "error": {
                    "grpcCode": 7,
                    "httpCode": 403,
                    "message": "PERMISSION_DENIED",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.RequestInfo",
                            "requestId": "abc123",
                        }
                    ],
                }
            },
        )
        
        validator = YandexGPTValidator()
        result = await validator.validate("test_token", folder_id="b1g123")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.PERMISSION_DENIED
        assert result.http_status == 403
        assert result.details["folder_id"] == "b1g123"
        assert result.details["request_id"] == "abc123"
    
    @pytest.mark.asyncio
    async def test_rate_limit(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test rate limit (429, grpc_code:8)."""
        httpx_mock.add_response(
            method="POST",
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            status_code=429,
            json={
                "error": {
                    "grpcCode": 8,
                    "httpCode": 429,
                    "message": "RESOURCE_EXHAUSTED",
                }
            },
        )
        
        validator = YandexGPTValidator()
        result = await validator.validate("test_token", folder_id="b1g123")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert result.retry_after == 10
    
    @pytest.mark.asyncio
    async def test_timeout(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test timeout handling."""
        httpx_mock.add_exception(
            method="POST",
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            exception=httpx.TimeoutException("Timeout"),
        )
        
        validator = YandexGPTValidator()
        result = await validator.validate("test_token", folder_id="b1g123")
        
        assert result.valid is False
        assert result.error_code == ErrorCode.NETWORK_TIMEOUT
        assert result.http_status == 504
    
    @pytest.mark.asyncio
    async def test_empty_api_key(self):
        """Test empty api_key raises ValueError."""
        validator = YandexGPTValidator()
        with pytest.raises(ValueError, match="api_key cannot be empty"):
            await validator.validate("", folder_id="b1g123")
    
    @pytest.mark.asyncio
    async def test_empty_folder_id(self):
        """Test empty folder_id raises ValueError."""
        validator = YandexGPTValidator()
        with pytest.raises(ValueError, match="folder_id cannot be empty"):
            await validator.validate("test_token", folder_id="")
    
    @pytest.mark.asyncio
    async def test_request_id_from_headers(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test request_id extraction from headers."""
        httpx_mock.add_response(
            method="POST",
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            status_code=500,
            headers={"x-request-id": "header-request-id"},
            json={
                "error": {
                    "grpcCode": 13,
                    "httpCode": 500,
                    "message": "INTERNAL",
                }
            },
        )
        
        validator = YandexGPTValidator()
        result = await validator.validate("test_token", folder_id="b1g123")
        
        assert result.details["request_id"] == "header-request-id"
```

---

### STEP 12: Обновить `README.md`

**Файл**: `README.md`

**Добавить раздел** после "Streaming Support" (перед "Provider Metrics & Monitoring"):

```markdown
## API Key Validation

Multi-LLM-Orchestrator provides validators for checking API keys before usage. This is especially useful for Platform SaaS applications where users need to validate their API keys during onboarding.

### Quick Start

```python
from orchestrator.validators import GigaChatValidator, YandexGPTValidator, ErrorCode

# GigaChat (with known scope)
validator = GigaChatValidator(verify_ssl=False)  # For Russian CA
result = await validator.validate(
    api_key="YOUR_API_KEY",
    scope="GIGACHAT_API_PERS"
)

if result.valid:
    print(f"✅ Valid! Scope: {result.details['scope']}")
elif result.error_code == ErrorCode.SCOPE_MISMATCH:
    print(f"❌ Scope mismatch: {result.message}")
elif result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED:
    print(f"⏳ Rate limited, retry after {result.retry_after}s")
else:
    print(f"❌ Error: {result.error_code.value} - {result.message}")

# YandexGPT
validator = YandexGPTValidator()
result = await validator.validate(
    api_key="YOUR_IAM_TOKEN",
    folder_id="YOUR_FOLDER_ID"
)

if result.valid:
    print("✅ Valid!")
elif result.error_code == ErrorCode.PERMISSION_DENIED:
    print(f"❌ No access to folder_id: {result.details['folder_id']}")
    print(f"Request ID: {result.details.get('request_id')}")
```

### Supported Providers

- **GigaChat**: Validates key with known scope (v0.8.0)
  - Requires `scope` parameter (GIGACHAT_API_PERS/B2B/CORP)
  - Supports `verify_ssl` parameter for Russian CA certificates
  - Returns `SCOPE_MISMATCH` if scope doesn't match key type

- **YandexGPT**: Validates IAM token and folder_id permissions (v0.8.0)
  - Requires `folder_id` parameter
  - Uses minimal request (maxTokens: 1) for cost efficiency
  - Extracts request_id from error responses for support

### Error Codes

- `SUCCESS`: Key is valid
- `INVALID_API_KEY`: 401 Unauthorized (invalid or expired key)
- `SCOPE_MISMATCH`: GigaChat scope conflict (400, code:7)
- `PERMISSION_DENIED`: YandexGPT folder_id access denied (403)
- `RATE_LIMIT_EXCEEDED`: 429 Too Many Requests (includes `retry_after`)
- `NETWORK_TIMEOUT`: Request timeout (default: 10s)
- `PROVIDER_ERROR`: 500+ Server error
- `VALIDATION_ERROR`: Unexpected error during validation

### Examples

See [validation_demo.py](examples/validation_demo.py) for complete examples.
```

---

### STEP 13: Создать `examples/validation_demo.py`

**Файл**: `examples/validation_demo.py`

**Содержимое**:

```python
"""
Demo: API Key Validation

Demonstrates how to validate GigaChat and YandexGPT API keys
before using them in production.

Usage:
    python examples/validation_demo.py
"""

import asyncio
from orchestrator.validators import (
    GigaChatValidator,
    YandexGPTValidator,
    ErrorCode,
)


async def main():
    print("=" * 60)
    print("API Key Validation Demo")
    print("=" * 60)
    
    # GigaChat validation
    print("\n### GigaChat Validation ###")
    print("Replace 'YOUR_GIGACHAT_KEY' with your actual API key")
    
    gc_validator = GigaChatValidator(verify_ssl=False)  # For Russian CA
    
    # Example: Valid key
    # result = await gc_validator.validate(
    #     api_key="YOUR_GIGACHAT_KEY",
    #     scope="GIGACHAT_API_PERS"
    # )
    # 
    # if result.valid:
    #     print(f"✅ Valid! Scope: {result.details.get('scope')}")
    # else:
    #     print(f"❌ Error: {result.error_code.value}")
    #     print(f"   Message: {result.message}")
    #     if result.retry_after:
    #         print(f"   Retry after: {result.retry_after}s")
    
    print("(Uncomment code above and add your API key to test)")
    
    # YandexGPT validation
    print("\n### YandexGPT Validation ###")
    print("Replace 'YOUR_IAM_TOKEN' and 'YOUR_FOLDER_ID' with actual values")
    
    yc_validator = YandexGPTValidator()
    
    # Example: Valid key
    # result = await yc_validator.validate(
    #     api_key="YOUR_IAM_TOKEN",
    #     folder_id="YOUR_FOLDER_ID"
    # )
    # 
    # if result.valid:
    #     print("✅ Valid!")
    # elif result.error_code == ErrorCode.PERMISSION_DENIED:
    #     print(f"❌ No access to folder_id: {result.details.get('folder_id')}")
    #     if result.details.get('request_id'):
    #         print(f"   Request ID: {result.details['request_id']}")
    # else:
    #     print(f"❌ Error: {result.error_code.value}")
    #     print(f"   Message: {result.message}")
    
    print("(Uncomment code above and add your credentials to test)")
    
    print("\n" + "=" * 60)
    print("For more examples, see the validators documentation.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

### STEP 14: Обновить `CHANGELOG.md`

**Файл**: `CHANGELOG.md`

**Добавить в начало** (после заголовка):

```markdown
## [0.8.0] - 2026-01-17

### Added
- **API Key Validators** module (`orchestrator.validators`)
  - `GigaChatValidator` for validating GigaChat API keys with known scope
  - `YandexGPTValidator` for validating YandexGPT IAM tokens and folder_id
  - Structured error types (`ValidationResult`, `ErrorCode`)
  - Support for `verify_ssl` parameter (GigaChat)
  - Request ID extraction for YandexGPT errors
  - Comprehensive test coverage (80%+)

### Changed
- Made `GigaChatProvider.get_access_token()` public (was `_get_access_token`)
  - Enables validators to reuse OAuth2 authentication logic
  - Maintains backward compatibility (internal method still works)

### Documentation
- Added "API Key Validation" section to README
- Added `examples/validation_demo.py` with usage examples
- Added Google-style docstrings to all validators

### Notes
- Scope auto-detection for GigaChat is planned for v0.8.1
- Validators are designed for Platform SaaS use cases (key validation during onboarding)
```

---

### STEP 15: Проверка coverage

**Команда**:

```bash
pytest tests/validators/ --cov=orchestrator.validators --cov-report=term-missing
```

**Цель**: 80%+ coverage

**Если coverage < 80%**:
- Добавить тесты для edge cases
- Добавить тесты для error scenarios
- Проверить все ветки кода

---

## ✅ CHECKLIST ПЕРЕД КОММИТОМ

- [ ] Все файлы созданы и реализованы
- [ ] Все тесты проходят (`pytest tests/validators/`)
- [ ] Coverage ≥ 80% (`pytest --cov=orchestrator.validators`)
- [ ] Существующие тесты проходят (`pytest tests/` - без validators)
- [ ] README.md обновлен
- [ ] CHANGELOG.md обновлен
- [ ] `examples/validation_demo.py` создан
- [ ] Docstrings добавлены (Google style)
- [ ] Type hints добавлены
- [ ] Линтер проходит (`ruff check src/orchestrator/validators/`)
- [ ] MyPy проходит (`mypy src/orchestrator/validators/`)

---

## 🚀 ГОТОВО К РЕАЛИЗАЦИИ

Все детали определены. Можно начинать реализацию по шагам выше.

**Важно**: Реализуй по порядку (Step 1 → Step 15), не пропускай шаги.
