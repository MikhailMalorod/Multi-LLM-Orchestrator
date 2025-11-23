"""Unit tests for YandexGPTProvider.

This module tests all YandexGPTProvider functionality including:
- IAM token authentication
- Text generation with various parameters
- Model URI building (automatic and full URI)
- Error handling and status code mapping
- Health check functionality
- Network error handling
- Configuration validation
"""

import httpx
import pytest
import pytest_httpx

from orchestrator.providers.base import (
    AuthenticationError,
    GenerationParams,
    InvalidRequestError,
    ProviderConfig,
    ProviderError,
    RateLimitError,
    TimeoutError,
)
from orchestrator.providers.yandexgpt import YandexGPTProvider


class TestYandexGPTProviderGenerate:
    """Test text generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_success(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test successful text generation.

        Verifies that generate() correctly sends request and parses response.
        """
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            json={
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "role": "assistant",
                                "text": "Test response"
                            },
                            "status": "ALTERNATIVE_STATUS_FINAL"
                        }
                    ],
                    "usage": {
                        "inputTextTokens": "10",
                        "completionTokens": "50",
                        "totalTokens": "60"
                    }
                }
            },
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        response = await provider.generate("test prompt")
        assert response == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_params(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test generation with custom GenerationParams.

        Verifies that temperature and max_tokens are correctly passed to API.
        """
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            json={
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "role": "assistant",
                                "text": "Response"
                            }
                        }
                    ]
                }
            },
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        params = GenerationParams(max_tokens=500, temperature=0.8)
        response = await provider.generate("test", params=params)
        assert response == "Response"

        # Verify request payload
        request = httpx_mock.get_request()
        assert request is not None
        import json
        payload = json.loads(request.content)
        assert payload["completionOptions"]["temperature"] == 0.8
        assert payload["completionOptions"]["maxTokens"] == 500

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test generation with custom model (yandexgpt-lite).

        Verifies that config.model is used in API request.
        """
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            json={
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "role": "assistant",
                                "text": "Response"
                            }
                        }
                    ]
                }
            },
        )

        config = ProviderConfig(
            name="yandexgpt",
            api_key="test_iam_token",
            folder_id="test_folder_id",
            model="yandexgpt-lite/latest"
        )
        provider = YandexGPTProvider(config)

        await provider.generate("test")

        # Verify modelUri in request
        request = httpx_mock.get_request()
        assert request is not None
        import json
        payload = json.loads(request.content)
        assert payload["modelUri"] == "gpt://test_folder_id/yandexgpt-lite/latest"

    @pytest.mark.asyncio
    async def test_generate_with_full_model_uri(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test generation with full model URI (gpt://...).

        Verifies that full URI in config.model is used as-is.
        """
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            json={
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "role": "assistant",
                                "text": "Response"
                            }
                        }
                    ]
                }
            },
        )

        config = ProviderConfig(
            name="yandexgpt",
            api_key="test_iam_token",
            folder_id="test_folder_id",
            model="gpt://custom_folder/custom_model/latest"
        )
        provider = YandexGPTProvider(config)

        await provider.generate("test")

        # Verify full URI is used as-is
        request = httpx_mock.get_request()
        assert request is not None
        import json
        payload = json.loads(request.content)
        assert payload["modelUri"] == "gpt://custom_folder/custom_model/latest"


class TestYandexGPTProviderErrors:
    """Test error handling and status code mapping."""

    @pytest.mark.asyncio
    async def test_error_400_invalid_request(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 400 Bad Request error."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=400,
            json={"message": "Invalid request format"},
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(InvalidRequestError, match="Bad request"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_401_authentication(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 401 Authentication error."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=401,
            json={"message": "Invalid or expired IAM token"},
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="invalid_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(AuthenticationError, match="Invalid or expired IAM token"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_403_access_denied(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 403 Access Denied error."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=403,
            json={"message": "Access denied"},
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="invalid_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(AuthenticationError, match="Access denied"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_404_model_not_found(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 404 Not Found error."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=404,
            json={"message": "Model not found"},
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(InvalidRequestError, match="Model not found"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_429_rate_limit(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 429 Rate Limit error."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=429,
            json={"message": "Rate limit exceeded"},
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_500_server_error(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 500 Server Error."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=500,
            json={"message": "Internal server error"},
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(ProviderError, match="Server error"):
            await provider.generate("test")


class TestYandexGPTProviderNetworkErrors:
    """Test network error handling."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of timeout errors."""
        httpx_mock.add_exception(
            httpx.TimeoutException("Request timed out"),
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(TimeoutError, match="timed out"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_connection_error(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of connection errors."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection failed"),
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(ProviderError, match="Connection error"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_network_error(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of network errors."""
        httpx_mock.add_exception(
            httpx.NetworkError("Network error"),
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(ProviderError, match="Network error"):
            await provider.generate("test")


class TestYandexGPTProviderHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test successful health check.

        Verifies that health_check() returns True when API request succeeds.
        """
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            json={
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "role": "assistant",
                                "text": "Hi"
                            }
                        }
                    ]
                }
            },
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        is_healthy = await provider.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test failed health check.

        Verifies that health_check() returns False when API request fails.
        """
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=401,
            json={"message": "Invalid token"},
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="invalid_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        is_healthy = await provider.health_check()
        assert is_healthy is False


class TestYandexGPTProviderConfig:
    """Test configuration handling."""

    def test_missing_api_key_raises_error(self) -> None:
        """Test that missing api_key raises ValueError."""
        config = ProviderConfig(name="yandexgpt", api_key=None, folder_id="test_folder_id")

        with pytest.raises(ValueError, match="api_key is required"):
            YandexGPTProvider(config)

    def test_missing_folder_id_raises_error(self) -> None:
        """Test that missing folder_id raises ValueError."""
        config = ProviderConfig(name="yandexgpt", api_key="test_iam_token", folder_id=None)

        with pytest.raises(ValueError, match="folder_id is required"):
            YandexGPTProvider(config)

    def test_build_model_uri_automatic(self) -> None:
        """Test automatic modelUri building from config."""
        config = ProviderConfig(
            name="yandexgpt",
            api_key="test_iam_token",
            folder_id="test_folder_id",
            model="yandexgpt/latest"
        )
        provider = YandexGPTProvider(config)

        uri = provider._build_model_uri()
        assert uri == "gpt://test_folder_id/yandexgpt/latest"

    def test_build_model_uri_default(self) -> None:
        """Test modelUri building with default model."""
        config = ProviderConfig(
            name="yandexgpt",
            api_key="test_iam_token",
            folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        uri = provider._build_model_uri()
        assert uri == "gpt://test_folder_id/yandexgpt/latest"

    def test_build_model_uri_full_uri(self) -> None:
        """Test modelUri building with full URI (gpt://...)."""
        config = ProviderConfig(
            name="yandexgpt",
            api_key="test_iam_token",
            folder_id="test_folder_id",
            model="gpt://custom_folder/custom_model/latest"
        )
        provider = YandexGPTProvider(config)

        uri = provider._build_model_uri()
        assert uri == "gpt://custom_folder/custom_model/latest"


class TestYandexGPTProviderResponseParsing:
    """Test response parsing and edge cases."""

    @pytest.mark.asyncio
    async def test_response_parsing_correct_structure(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test parsing of correct response structure."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            json={
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "role": "assistant",
                                "text": "Correct response"
                            },
                            "status": "ALTERNATIVE_STATUS_FINAL"
                        }
                    ],
                    "usage": {
                        "inputTextTokens": "10",
                        "completionTokens": "50",
                        "totalTokens": "60"
                    }
                }
            },
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        response = await provider.generate("test")
        assert response == "Correct response"

    @pytest.mark.asyncio
    async def test_response_parsing_invalid_json(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of invalid JSON response."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            status_code=200,
            text="Invalid JSON response",
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(ProviderError, match="Invalid response format"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_response_parsing_missing_fields(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of response with missing required fields."""
        httpx_mock.add_response(
            url="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            method="POST",
            json={"result": {}},  # Missing alternatives
        )

        config = ProviderConfig(
            name="yandexgpt", api_key="test_iam_token", folder_id="test_folder_id"
        )
        provider = YandexGPTProvider(config)

        with pytest.raises(ProviderError, match="Invalid response format"):
            await provider.generate("test")

