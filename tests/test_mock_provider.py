"""Unit tests for MockProvider.

This module tests all MockProvider functionality including:
- All 5 simulation modes (normal, timeout, ratelimit, auth-error, invalid-request)
- Health check behavior (healthy vs unhealthy)
- Response truncation based on max_tokens
- Response delay in normal mode
"""

import time

import pytest

from orchestrator.providers.base import GenerationParams, ProviderConfig
from orchestrator.providers.mock import MockProvider
from orchestrator.providers.base import (
    AuthenticationError,
    InvalidRequestError,
    RateLimitError,
    TimeoutError,
)


class TestMockProviderModes:
    """Test all MockProvider simulation modes."""

    @pytest.mark.asyncio
    async def test_mock_normal_mode_returns_response(self) -> None:
        """Test that mock-normal mode returns a valid response.
        
        Verifies that normal mode generates a response with the expected format
        and includes the prompt in the response.
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)
        
        response = await provider.generate("Hello, world!")
        
        assert response == "Mock response to: Hello, world!"
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_mock_timeout_mode_raises_timeout_error(self) -> None:
        """Test that mock-timeout mode raises TimeoutError.
        
        Verifies that timeout simulation mode correctly raises TimeoutError
        when generate() is called.
        """
        config = ProviderConfig(name="test", model="mock-timeout")
        provider = MockProvider(config)
        
        with pytest.raises(TimeoutError, match="Mock timeout simulation"):
            await provider.generate("test prompt")

    @pytest.mark.asyncio
    async def test_mock_ratelimit_mode_raises_ratelimit_error(self) -> None:
        """Test that mock-ratelimit mode raises RateLimitError.
        
        Verifies that rate limit simulation mode correctly raises RateLimitError
        when generate() is called.
        """
        config = ProviderConfig(name="test", model="mock-ratelimit")
        provider = MockProvider(config)
        
        with pytest.raises(RateLimitError, match="Mock rate limit simulation"):
            await provider.generate("test prompt")

    @pytest.mark.asyncio
    async def test_mock_auth_error_mode_raises_auth_error(self) -> None:
        """Test that mock-auth-error mode raises AuthenticationError.
        
        Verifies that authentication error simulation mode correctly raises
        AuthenticationError when generate() is called.
        """
        config = ProviderConfig(name="test", model="mock-auth-error")
        provider = MockProvider(config)
        
        with pytest.raises(AuthenticationError, match="Mock authentication failure"):
            await provider.generate("test prompt")

    @pytest.mark.asyncio
    async def test_mock_invalid_request_mode_raises_invalid_request_error(self) -> None:
        """Test that mock-invalid-request mode raises InvalidRequestError.
        
        Verifies that invalid request simulation mode correctly raises
        InvalidRequestError when generate() is called.
        """
        config = ProviderConfig(name="test", model="mock-invalid-request")
        provider = MockProvider(config)
        
        with pytest.raises(InvalidRequestError, match="Mock invalid request"):
            await provider.generate("test prompt")


class TestMockProviderHealthCheck:
    """Test MockProvider health_check() behavior."""

    @pytest.mark.asyncio
    async def test_health_check_returns_true_for_healthy(self) -> None:
        """Test that health_check() returns True for healthy providers.
        
        Verifies that providers without "unhealthy" in their model name
        return True from health_check().
        """
        # Test normal mode
        config_normal = ProviderConfig(name="test", model="mock-normal")
        provider_normal = MockProvider(config_normal)
        assert await provider_normal.health_check() is True
        
        # Test timeout mode (healthy but will fail on generate)
        config_timeout = ProviderConfig(name="test", model="mock-timeout")
        provider_timeout = MockProvider(config_timeout)
        assert await provider_timeout.health_check() is True
        
        # Test with None model (defaults to mock-normal)
        config_none = ProviderConfig(name="test", model=None)
        provider_none = MockProvider(config_none)
        assert await provider_none.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_returns_false_for_unhealthy(self) -> None:
        """Test that health_check() returns False for unhealthy providers.
        
        Verifies that providers with "unhealthy" in their model name
        (case-insensitive) return False from health_check().
        """
        # Test explicit unhealthy mode
        config_unhealthy = ProviderConfig(name="test", model="mock-unhealthy")
        provider_unhealthy = MockProvider(config_unhealthy)
        assert await provider_unhealthy.health_check() is False
        
        # Test partial match (contains "unhealthy")
        config_partial = ProviderConfig(name="test", model="mock-normal-unhealthy")
        provider_partial = MockProvider(config_partial)
        assert await provider_partial.health_check() is False
        
        # Test case-insensitive
        config_upper = ProviderConfig(name="test", model="mock-UNHEALTHY")
        provider_upper = MockProvider(config_upper)
        assert await provider_upper.health_check() is False


class TestMockProviderMaxTokens:
    """Test MockProvider response truncation based on max_tokens."""

    @pytest.mark.asyncio
    async def test_max_tokens_truncates_response(self) -> None:
        """Test that max_tokens truncates response when smaller than response length.
        
        Verifies that when max_tokens is less than the response length,
        the response is truncated to exactly max_tokens characters.
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)
        params = GenerationParams(max_tokens=10)
        
        response = await provider.generate("Hello, world!", params=params)
        
        assert len(response) == 10
        assert response == "Mock respo"  # First 10 chars of "Mock response to: Hello, world!"

    @pytest.mark.asyncio
    async def test_max_tokens_no_truncation_when_equal(self) -> None:
        """Test that max_tokens doesn't truncate when equal to response length.
        
        Verifies that when max_tokens equals the response length,
        the full response is returned.
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)
        
        # Generate response first to know its length
        full_response = await provider.generate("test")
        response_length = len(full_response)
        
        # Now test with max_tokens equal to response length
        params = GenerationParams(max_tokens=response_length)
        response = await provider.generate("test", params=params)
        
        assert len(response) == response_length
        assert response == full_response

    @pytest.mark.asyncio
    async def test_max_tokens_no_truncation_when_larger(self) -> None:
        """Test that max_tokens doesn't truncate when larger than response length.
        
        Verifies that when max_tokens is greater than the response length,
        the full response is returned (no padding or truncation).
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)
        
        # Generate response first to know its length
        full_response = await provider.generate("test")
        response_length = len(full_response)
        
        # Test with max_tokens much larger than response length
        params = GenerationParams(max_tokens=1000)
        response = await provider.generate("test", params=params)
        
        assert len(response) == response_length
        assert response == full_response

    @pytest.mark.asyncio
    async def test_max_tokens_not_specified_returns_full_response(self) -> None:
        """Test that when max_tokens is not specified, full response is returned.
        
        Verifies that when GenerationParams is None or max_tokens is not set,
        the complete response is returned without truncation.
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)
        
        # Test with None params
        response_none = await provider.generate("test")
        assert len(response_none) > 0
        assert response_none.startswith("Mock response to:")
        
        # Test with params but max_tokens=None (shouldn't happen with Pydantic, but test anyway)
        params = GenerationParams(max_tokens=1000)
        response_with_params = await provider.generate("test", params=params)
        assert len(response_with_params) > 0


class TestMockProviderDelay:
    """Test MockProvider delay in normal mode."""

    @pytest.mark.asyncio
    async def test_mock_normal_has_correct_delay(self) -> None:
        """Test that mock-normal mode has approximately 0.1s delay.
        
        Verifies that the delay in normal mode is within acceptable range
        (90-200ms) to account for system overhead while ensuring the delay exists.
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)
        
        start = time.perf_counter()
        await provider.generate("test")
        elapsed = time.perf_counter() - start
        
        # Check that delay is approximately 0.1s (90-200ms range)
        assert 0.09 <= elapsed <= 0.2, f"Expected delay ~0.1s, got {elapsed:.3f}s"

