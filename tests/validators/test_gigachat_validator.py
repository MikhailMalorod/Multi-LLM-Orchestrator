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

    # ========== Auto-Detection Tests (v0.8.1+) ==========

    @pytest.mark.asyncio
    async def test_auto_detect_pers_first_try(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect PERS (first try success)."""
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

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is True
        assert result.error_code == ErrorCode.SUCCESS
        assert result.details["detected_scope"] == "GIGACHAT_API_PERS"
        assert result.details["auto_detection_used"] is True
        assert result.details["attempts_count"] == 1
        assert result.details["total_time_ms"] >= 0
        assert result.details["attempted_scopes"] == ["GIGACHAT_API_PERS"]

    @pytest.mark.asyncio
    async def test_auto_detect_b2b_second_try(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect B2B (second try success: PERS → 400+code:7, B2B → 200)."""
        # PERS attempt: OAuth2 success, /models → 400+code:7
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: OAuth2 success, /models → 200
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

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is True
        assert result.error_code == ErrorCode.SUCCESS
        assert result.details["detected_scope"] == "GIGACHAT_API_B2B"
        assert result.details["auto_detection_used"] is True
        assert result.details["attempts_count"] == 2
        assert result.details["attempted_scopes"] == ["GIGACHAT_API_PERS", "GIGACHAT_API_B2B"]

    @pytest.mark.asyncio
    async def test_auto_detect_corp_third_try(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect CORP (third try success: PERS → 400+code:7, B2B → 400+code:7, CORP → 200)."""
        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token2", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # CORP attempt: success
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token3", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=200,
            json={"data": [{"id": "GigaChat"}]},
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is True
        assert result.error_code == ErrorCode.SUCCESS
        assert result.details["detected_scope"] == "GIGACHAT_API_CORP"
        assert result.details["attempts_count"] == 3
        assert result.details["attempted_scopes"] == [
            "GIGACHAT_API_PERS",
            "GIGACHAT_API_B2B",
            "GIGACHAT_API_CORP",
        ]

    @pytest.mark.asyncio
    async def test_auto_detect_fails_all_scopes(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect fails (all 3 scopes → 400+code:7)."""
        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token2", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # CORP attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token3", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is False
        assert result.error_code == ErrorCode.SCOPE_MISMATCH
        assert result.details["auto_detection_used"] is True
        assert result.details["auto_detection_stopped"] is True
        assert result.details["stopped_reason"] == "scope_mismatch"
        assert result.details["attempts_count"] == 3
        assert len(result.details["attempted_scopes"]) == 3

    @pytest.mark.asyncio
    async def test_auto_detect_stops_on_401(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect stops on 401 (invalid key, first scope)."""
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=401,
        )

        validator = GigaChatValidator()
        result = await validator.validate("invalid_key")

        assert result.valid is False
        assert result.error_code == ErrorCode.INVALID_API_KEY
        assert result.details["auto_detection_used"] is True
        assert result.details["auto_detection_stopped"] is True
        assert result.details["stopped_reason"] == "invalid_api_key"
        assert result.details["attempts_count"] == 1
        assert result.details["attempted_scopes"] == ["GIGACHAT_API_PERS"]

    @pytest.mark.asyncio
    async def test_auto_detect_stops_on_429_at_models(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect stops on 429 at /models (rate limit, second scope)."""
        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: rate limit at /models
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token2", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=429,
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is False
        assert result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert result.retry_after == 30
        assert result.details["auto_detection_stopped"] is True
        assert result.details["stopped_reason"] == "rate_limit_exceeded"
        assert result.details["attempts_count"] == 2
        assert result.details["attempted_scopes"] == ["GIGACHAT_API_PERS", "GIGACHAT_API_B2B"]

    @pytest.mark.asyncio
    async def test_auto_detect_stops_on_timeout(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect stops on timeout (timeout, first scope)."""
        httpx_mock.add_exception(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            exception=httpx.TimeoutException("Timeout"),
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is False
        assert result.error_code == ErrorCode.NETWORK_TIMEOUT
        assert result.http_status == 504
        assert result.details["auto_detection_stopped"] is True
        assert result.details["stopped_reason"] == "timeout"
        assert result.details["attempts_count"] == 1

    @pytest.mark.asyncio
    async def test_backward_compatibility_explicit_scope(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test backward compatibility (explicit scope, no auto-detection, callback not called)."""
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

        callback_called = []

        def callback(scope: str, current: int, total: int):
            callback_called.append((scope, current, total))

        validator = GigaChatValidator()
        result = await validator.validate("test_key", scope="GIGACHAT_API_PERS", on_scope_attempt=callback)

        assert result.valid is True
        assert result.details["scope"] == "GIGACHAT_API_PERS"
        assert result.details["auto_detection_used"] is False
        assert callback_called == []  # Callback should NOT be called for explicit scope

    @pytest.mark.asyncio
    async def test_auto_detect_stops_on_429_at_oauth2(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect stops on 429 at OAuth2 endpoint (not /models)."""
        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: rate limit at OAuth2 endpoint
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=429,
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is False
        assert result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED
        assert result.details["auto_detection_stopped"] is True
        assert result.details["stopped_reason"] == "rate_limit_exceeded"
        assert result.details["attempts_count"] == 2

    @pytest.mark.asyncio
    async def test_auto_detect_stops_on_timeout_second_scope(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect stops on timeout at second scope (B2B)."""
        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: timeout
        httpx_mock.add_exception(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            exception=httpx.TimeoutException("Timeout"),
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is False
        assert result.error_code == ErrorCode.NETWORK_TIMEOUT
        assert result.details["stopped_reason"] == "timeout"
        assert result.details["attempts_count"] == 2
        assert result.details["attempted_scopes"] == ["GIGACHAT_API_PERS", "GIGACHAT_API_B2B"]

    @pytest.mark.asyncio
    async def test_auto_detect_different_error_messages(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test auto-detect with different error messages per scope (all 400, but different messages)."""
        # PERS attempt: scope mismatch with message 1
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope PERS not valid"},
        )

        # B2B attempt: scope mismatch with message 2
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token2", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope B2B not valid"},
        )

        # CORP attempt: scope mismatch with message 3
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token3", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope CORP not valid"},
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is False
        assert result.error_code == ErrorCode.SCOPE_MISMATCH
        assert result.details["stopped_reason"] == "scope_mismatch"
        assert result.details["attempts_count"] == 3

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test that on_scope_attempt callback is called for each attempt."""
        progress_calls = []

        def track_progress(scope: str, current: int, total: int):
            progress_calls.append((scope, current, total))

        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: success
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

        validator = GigaChatValidator()
        result = await validator.validate("test_key", on_scope_attempt=track_progress)

        assert result.valid is True
        assert progress_calls == [
            ("GIGACHAT_API_PERS", 1, 3),
            ("GIGACHAT_API_B2B", 2, 3),
        ]

    @pytest.mark.asyncio
    async def test_metrics_in_details(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test that details contains all required metrics."""
        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: success
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

        validator = GigaChatValidator()
        result = await validator.validate("test_key")

        assert result.valid is True
        assert result.details["auto_detection_used"] is True
        assert result.details["detected_scope"] == "GIGACHAT_API_B2B"
        assert result.details["attempts_count"] == 2
        assert "total_time_ms" in result.details
        assert result.details["total_time_ms"] >= 0
        assert result.details["attempted_scopes"] == ["GIGACHAT_API_PERS", "GIGACHAT_API_B2B"]

    @pytest.mark.asyncio
    async def test_callback_called_before_timeout(self, httpx_mock: pytest_httpx.HTTPXMock):
        """Test callback called before timeout error."""
        progress_calls = []

        def track_progress(scope: str, current: int, total: int):
            progress_calls.append((scope, current, total))

        # PERS attempt: scope mismatch
        httpx_mock.add_response(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            status_code=200,
            json={"access_token": "mock_token1", "expires_at": 1234567890},
        )
        httpx_mock.add_response(
            method="GET",
            url="https://gigachat.devices.sberbank.ru/api/v1/models",
            status_code=400,
            json={"code": 7, "message": "Scope mismatch"},
        )

        # B2B attempt: timeout
        httpx_mock.add_exception(
            method="POST",
            url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            exception=httpx.TimeoutException("Timeout"),
        )

        validator = GigaChatValidator()
        result = await validator.validate("test_key", on_scope_attempt=track_progress)

        assert result.valid is False
        assert result.error_code == ErrorCode.NETWORK_TIMEOUT
        # Callback should be called for PERS and B2B (before timeout)
        assert len(progress_calls) == 2
        assert progress_calls[0] == ("GIGACHAT_API_PERS", 1, 3)
        assert progress_calls[1] == ("GIGACHAT_API_B2B", 2, 3)
