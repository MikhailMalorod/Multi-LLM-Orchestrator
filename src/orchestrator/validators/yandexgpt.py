"""YandexGPT API key validator.

This module provides YandexGPTValidator for validating YandexGPT
IAM tokens and folder_id permissions.
"""

from typing import Any

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

    def _extract_request_id(self, response: httpx.Response) -> str | None:
        """Extract request_id from response (headers or error body).
        
        Args:
            response: HTTPX response object
        
        Returns:
            Request ID string if found, None otherwise
        """
        # Try headers first
        request_id = response.headers.get("x-request-id")
        if request_id:
            return str(request_id)

        # Try error body (google.rpc.RequestInfo)
        try:
            error_data = response.json().get("error", {})
            details = error_data.get("details", [])
            for detail in details:
                if detail.get("@type") == "type.googleapis.com/google.rpc.RequestInfo":
                    request_id_value = detail.get("requestId")
                    if request_id_value:
                        return str(request_id_value)
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

    async def validate(  # type: ignore[override]
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
