"""Tests for YandexGPTValidator."""

import httpx
import pytest
import pytest_httpx

from orchestrator.validators import ErrorCode, YandexGPTValidator


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

    @pytest.mark.asyncio
    async def test_request_id_from_error_body(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test request_id extraction from error body."""
        httpx_mock.add_response(
            method="POST",
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            status_code=500,
            json={
                "error": {
                    "grpcCode": 13,
                    "httpCode": 500,
                    "message": "INTERNAL",
                    "details": [
                        {
                            "@type": "type.googleapis.com/google.rpc.RequestInfo",
                            "requestId": "body-request-id",
                        }
                    ],
                }
            },
        )

        validator = YandexGPTValidator()
        result = await validator.validate("test_token", folder_id="b1g123")

        assert result.details["request_id"] == "body-request-id"

    @pytest.mark.asyncio
    async def test_minimal_request_body(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test that request body uses minimal tokens."""
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
        await validator.validate("test_token", folder_id="b1g123")

        # Verify request payload
        request = httpx_mock.get_request()
        assert request is not None
        import json
        payload = json.loads(request.content)
        assert payload["completionOptions"]["maxTokens"] == 1
        assert payload["completionOptions"]["temperature"] == 0.1
        assert payload["modelUri"] == "gpt://b1g123/yandexgpt-lite/latest"
        assert payload["messages"][0]["text"] == "test"
