"""Tests for GigaChatValidator."""

import httpx
import pytest
import pytest_httpx

from orchestrator.validators import ErrorCode, GigaChatValidator


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
        assert result.details["error_code"] == 7

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

    @pytest.mark.asyncio
    async def test_verify_ssl_parameter(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test verify_ssl parameter."""
        # Mock responses for first call
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token", "expires_at": 1234567890},
        )

        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=200,
            json={"data": [{"id": "GigaChat"}]},
        )

        # Test with verify_ssl=False
        validator = GigaChatValidator(verify_ssl=False)
        result = await validator.validate("test_key", scope="GIGACHAT_API_PERS")
        assert result.valid is True

        # Mock responses for second call (override via kwargs)
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token2", "expires_at": 1234567890},
        )

        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=200,
            json={"data": [{"id": "GigaChat"}]},
        )

        # Test override via kwargs
        validator2 = GigaChatValidator(verify_ssl=True)
        result2 = await validator2.validate("test_key", scope="GIGACHAT_API_PERS", verify_ssl=False)
        assert result2.valid is True

    @pytest.mark.asyncio
    async def test_server_error(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test server error (500+)."""
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token", "expires_at": 1234567890},
        )

        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=500,
            json={"message": "Internal server error"},
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key", scope="GIGACHAT_API_PERS")

        assert result.valid is False
        assert result.error_code == ErrorCode.PROVIDER_ERROR
        assert result.http_status == 500
