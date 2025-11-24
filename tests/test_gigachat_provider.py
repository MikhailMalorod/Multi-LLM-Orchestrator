"""Unit tests for GigaChatProvider.

This module tests all GigaChatProvider functionality including:
- OAuth2 token management and refresh
- Text generation with various parameters
- Automatic token refresh on 401 errors
- Error handling and status code mapping
- Health check functionality
- Network error handling
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
from orchestrator.providers.gigachat import GigaChatProvider


class TestGigaChatProviderOAuth2:
    """Test OAuth2 token management."""

    @pytest.mark.asyncio
    async def test_successful_token_acquisition(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test successful OAuth2 token acquisition.

        Verifies that provider correctly requests and stores OAuth2 token
        from the OAuth2 endpoint.
        """
        # Mock OAuth2 endpoint
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "test_token_123", "expires_at": 9999999999000},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        # Token should be acquired on first generate() call
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"content": "Test response"}}]},
        )

        response = await provider.generate("test")
        assert response == "Test response"
        assert provider._access_token == "test_token_123"

    @pytest.mark.asyncio
    async def test_invalid_authorization_key(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of invalid authorization key.

        Verifies that 401 from OAuth2 endpoint raises AuthenticationError.
        """
        # Mock OAuth2 endpoint with 401
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            status_code=401,
            json={"message": "Invalid authorization key"},
        )

        config = ProviderConfig(name="gigachat", api_key="invalid_key")
        provider = GigaChatProvider(config)

        with pytest.raises(AuthenticationError, match="Invalid authorization key"):
            await provider._ensure_access_token()

    @pytest.mark.asyncio
    async def test_token_refresh_on_expiration(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test automatic token refresh when token expires.

        Verifies that provider automatically refreshes token when it expires
        (expires_at in the past).
        """
        import time

        # Mock OAuth2 endpoint - first token request
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token1", "expires_at": int(time.time() * 1000) - 1000},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        # First generate() - will get token1 (expired)
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"content": "Response 1"}}]},
        )

        await provider.generate("test1")
        assert provider._access_token == "token1"

        # Mock OAuth2 endpoint - token refresh
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token2", "expires_at": 9999999999000},
        )

        # Second generate() - should refresh token
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"content": "Response 2"}}]},
        )

        response = await provider.generate("test2")
        assert response == "Response 2"
        assert provider._access_token == "token2"


class TestGigaChatProviderGenerate:
    """Test text generation functionality."""

    @pytest.mark.asyncio
    async def test_generate_success(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test successful text generation.

        Verifies that generate() correctly sends request and parses response.
        """
        # Mock OAuth2
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "test_token", "expires_at": 9999999999000},
        )

        # Mock API
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"content": "Test response"}}]},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        response = await provider.generate("test prompt")
        assert response == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_params(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test generation with custom GenerationParams.

        Verifies that all generation parameters are correctly passed to API.
        """
        # Mock OAuth2
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "test_token", "expires_at": 9999999999000},
        )

        # Mock API
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"content": "Response"}}]},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        params = GenerationParams(
            max_tokens=500, temperature=0.8, top_p=0.9, stop=["###", "END"]
        )
        response = await provider.generate("test", params=params)
        assert response == "Response"

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test generation with custom model from config.

        Verifies that config.model is used in API request.
        """
        # Mock OAuth2
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "test_token", "expires_at": 9999999999000},
        )

        # Mock API
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"content": "Response"}}]},
        )

        config = ProviderConfig(
            name="gigachat", api_key="test_key", model="GigaChat-Pro"
        )
        provider = GigaChatProvider(config)

        await provider.generate("test")

    @pytest.mark.asyncio
    async def test_generate_token_refresh_on_401(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test automatic token refresh when 401 occurs during generate().

        Verifies that provider automatically refreshes token and retries request
        when 401 error occurs during API call.
        """
        # Mock OAuth2 - initial token (will be requested first)
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "old_token", "expires_at": 9999999999000},
        )

        # Mock API - first request returns 401 (token expired during request)
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=401,
            json={"message": "Token expired"},
        )

        # Mock OAuth2 - token refresh (called after 401)
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "new_token", "expires_at": 9999999999000},
        )

        # Mock API - retry after refresh succeeds
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            json={"choices": [{"message": {"content": "Success after refresh"}}]},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        # First call will get old_token, then 401, then refresh to new_token, then retry
        response = await provider.generate("test")
        assert response == "Success after refresh"
        # Token should be updated after refresh
        assert provider._access_token == "new_token"


class TestGigaChatProviderErrors:
    """Test error handling and status code mapping."""

    @pytest.mark.asyncio
    async def test_error_400_invalid_request(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 400 Bad Request error."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=400,
            json={"message": "Invalid request format"},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(InvalidRequestError, match="Bad request"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_401_authentication(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 401 Authentication error after retry."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        # First 401 triggers refresh
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=401,
            json={"message": "Token expired"},
        )

        # Token refresh
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "new_token", "expires_at": 9999999999000},
        )

        # Retry also returns 401
        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=401,
            json={"message": "Authentication failed"},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_404_invalid_model(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 404 Not Found error."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=404,
            json={"message": "Model not found"},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(InvalidRequestError, match="Invalid model"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_422_validation(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 422 Validation Error."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=422,
            json={"message": "Validation error"},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(InvalidRequestError, match="Validation error"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_429_rate_limit(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 429 Rate Limit error."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=429,
            json={"message": "Rate limit exceeded"},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_error_500_server_error(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of 500 Server Error."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        httpx_mock.add_response(
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            method="POST",
            status_code=500,
            json={"message": "Internal server error"},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(ProviderError, match="Server error"):
            await provider.generate("test")


class TestGigaChatProviderNetworkErrors:
    """Test network error handling."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of timeout errors."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        # Simulate timeout
        httpx_mock.add_exception(
            httpx.TimeoutException("Request timed out"),
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(TimeoutError, match="timed out"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_connection_error(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test handling of connection errors."""
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        # Simulate connection error
        httpx_mock.add_exception(
            httpx.ConnectError("Connection failed"),
            url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        with pytest.raises(ProviderError, match="Connection error"):
            await provider.generate("test")


class TestGigaChatProviderHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test successful health check.

        Verifies that health_check() returns True when OAuth2 token can be obtained.
        """
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            json={"access_token": "token", "expires_at": 9999999999000},
        )

        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        is_healthy = await provider.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, httpx_mock: pytest_httpx.HTTPXMock) -> None:
        """Test failed health check.

        Verifies that health_check() returns False when OAuth2 fails.
        """
        httpx_mock.add_response(
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            method="POST",
            status_code=401,
            json={"message": "Invalid key"},
        )

        config = ProviderConfig(name="gigachat", api_key="invalid_key")
        provider = GigaChatProvider(config)

        is_healthy = await provider.health_check()
        assert is_healthy is False


class TestGigaChatProviderConfig:
    """Test configuration handling."""

    def test_missing_api_key_raises_error(self) -> None:
        """Test that missing api_key raises ValueError."""
        config = ProviderConfig(name="gigachat", api_key=None)

        with pytest.raises(ValueError, match="api_key is required"):
            GigaChatProvider(config)

    def test_custom_scope(self) -> None:
        """Test that custom scope is used."""
        config = ProviderConfig(
            name="gigachat", api_key="test_key", scope="GIGACHAT_API_CORP"
        )
        provider = GigaChatProvider(config)

        # Scope is stored in config, will be used in OAuth2 request
        assert provider.config.scope == "GIGACHAT_API_CORP"

    def test_default_scope(self) -> None:
        """Test that default scope is used when not specified."""
        config = ProviderConfig(name="gigachat", api_key="test_key")
        provider = GigaChatProvider(config)

        # Should use DEFAULT_SCOPE when config.scope is None
        assert provider.config.scope is None
        assert provider.DEFAULT_SCOPE == "GIGACHAT_API_PERS"

    def test_gigachat_provider_with_verify_ssl_true(self) -> None:
        """Test GigaChatProvider with SSL verification enabled (default)."""
        config = ProviderConfig(
            name="test",
            api_key="test_key",
            scope="GIGACHAT_API_PERS",
            verify_ssl=True  # Explicit True
        )
        provider = GigaChatProvider(config)
        assert provider.config.verify_ssl is True

    def test_gigachat_provider_with_verify_ssl_false(self) -> None:
        """Test GigaChatProvider with SSL verification disabled."""
        config = ProviderConfig(
            name="test",
            api_key="test_key",
            scope="GIGACHAT_API_PERS",
            verify_ssl=False
        )
        provider = GigaChatProvider(config)
        assert provider.config.verify_ssl is False

