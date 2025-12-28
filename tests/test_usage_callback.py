"""Unit tests for usage callback functionality.

This module tests both Python callback and HTTP POST callback functionality
for usage tracking in Router.
"""

import pytest
from pytest_httpx import HTTPXMock

from orchestrator import Router, UsageData
from orchestrator.providers.base import ProviderConfig, TimeoutError
from orchestrator.providers.mock import MockProvider


class TestPythonCallback:
    """Test Python callback functionality."""

    @pytest.mark.asyncio
    async def test_python_callback_invoked_on_success(self) -> None:
        """Test that Python callback is invoked with correct data on success."""
        callback_data: list[UsageData] = []

        async def track_usage(data: UsageData) -> None:
            callback_data.append(data)

        router = Router(strategy="round-robin", usage_callback=track_usage)
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        response = await router.route("test prompt")

        assert len(callback_data) == 1
        assert callback_data[0].success is True
        assert callback_data[0].streaming is False
        assert callback_data[0].error_type is None
        assert callback_data[0].provider_name == "provider1"
        assert callback_data[0].model == "mock-normal"
        assert callback_data[0].prompt_tokens > 0
        assert callback_data[0].completion_tokens > 0
        assert callback_data[0].total_tokens > 0
        assert response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_python_callback_invoked_on_error(self) -> None:
        """Test that Python callback is invoked with error data on failure."""
        callback_data: list[UsageData] = []

        async def track_usage(data: UsageData) -> None:
            callback_data.append(data)

        router = Router(strategy="round-robin", usage_callback=track_usage)
        config = ProviderConfig(name="provider1", model="mock-timeout")
        router.add_provider(MockProvider(config))

        with pytest.raises(TimeoutError):
            await router.route("test prompt")

        # Callback should be invoked even for failed requests
        assert len(callback_data) == 1
        assert callback_data[0].success is False
        assert callback_data[0].error_type == "TimeoutError"
        assert callback_data[0].prompt_tokens == 0
        assert callback_data[0].completion_tokens == 0
        assert callback_data[0].cost == 0.0

    @pytest.mark.asyncio
    async def test_python_callback_invoked_in_streaming(self) -> None:
        """Test that Python callback is invoked for streaming requests."""
        callback_data: list[UsageData] = []

        async def track_usage(data: UsageData) -> None:
            callback_data.append(data)

        router = Router(strategy="round-robin", usage_callback=track_usage)
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        chunks = []
        async for chunk in router.route_stream("test prompt"):
            chunks.append(chunk)

        assert len(callback_data) == 1
        assert callback_data[0].streaming is True
        assert callback_data[0].success is True
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_python_callback_invoked_for_each_provider_in_fallback(
        self,
    ) -> None:
        """Test that callback is invoked for each provider in fallback chain."""
        callback_data: list[UsageData] = []

        async def track_usage(data: UsageData) -> None:
            callback_data.append(data)

        router = Router(strategy="round-robin", usage_callback=track_usage)
        # Add: timeout provider (will fail), then normal provider (will succeed)
        router.add_provider(
            MockProvider(ProviderConfig(name="p1", model="mock-timeout"))
        )
        router.add_provider(
            MockProvider(ProviderConfig(name="p2", model="mock-normal"))
        )

        response = await router.route("test")

        # Should have 2 callbacks: p1 (error) + p2 (success)
        assert len(callback_data) == 2
        assert callback_data[0].provider_name == "p1"
        assert callback_data[0].success is False
        assert callback_data[0].error_type == "TimeoutError"
        assert callback_data[1].provider_name == "p2"
        assert callback_data[1].success is True
        assert response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_python_callback_error_does_not_break_request(self) -> None:
        """Test that errors in callback don't break the main request flow."""
        async def failing_callback(data: UsageData) -> None:
            raise ValueError("Callback error")

        router = Router(strategy="round-robin", usage_callback=failing_callback)
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        # Request should succeed despite callback error
        response = await router.route("test prompt")
        assert response.startswith("Mock response to:")


class TestHTTPCallback:
    """Test HTTP POST callback functionality."""

    @pytest.mark.asyncio
    async def test_http_callback_invoked_on_success(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that HTTP POST callback is invoked with correct payload."""
        httpx_mock.add_response(status_code=200)

        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
        )
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        await router.route("test prompt")

        # Verify POST was called
        assert len(httpx_mock.get_requests()) == 1
        request = httpx_mock.get_requests()[0]
        assert str(request.url) == "https://api.example.com/usage"
        assert request.method == "POST"

        # Verify payload structure
        import json

        payload = json.loads(request.read().decode())
        assert payload["provider"] == "provider1"
        assert payload["model"] == "mock-normal"
        assert payload["success"] is True
        assert payload["streaming"] is False
        assert "prompt_tokens" in payload
        assert "completion_tokens" in payload
        assert "total_tokens" in payload
        assert "cost" in payload
        assert "latency_ms" in payload
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_http_callback_invoked_on_error(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that HTTP callback is invoked with error data on failure."""
        httpx_mock.add_response(status_code=200)

        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
        )
        config = ProviderConfig(name="provider1", model="mock-timeout")
        router.add_provider(MockProvider(config))

        with pytest.raises(TimeoutError):
            await router.route("test prompt")

        # Verify POST was called
        assert len(httpx_mock.get_requests()) == 1
        request = httpx_mock.get_requests()[0]

        import json

        payload = json.loads(request.read().decode())
        assert payload["success"] is False
        assert payload["error_type"] == "TimeoutError"
        assert payload["prompt_tokens"] == 0
        assert payload["completion_tokens"] == 0
        assert payload["cost"] == 0.0

    @pytest.mark.asyncio
    async def test_http_callback_includes_tenant_and_key_id(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that HTTP callback includes tenant_id and platform_key_id."""
        httpx_mock.add_response(status_code=200)

        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
            tenant_id="tenant-123",
            platform_key_id="key-456",
        )
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        await router.route("test prompt")

        request = httpx_mock.get_requests()[0]

        import json

        payload = json.loads(request.read().decode())
        assert payload["tenant_id"] == "tenant-123"
        assert payload["platform_key_id"] == "key-456"

    @pytest.mark.asyncio
    async def test_http_callback_timeout_does_not_break_request(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that HTTP callback timeout doesn't break the main request."""
        # Simulate timeout by not adding a response
        # httpx will timeout after 5 seconds, but we'll use a shorter timeout
        import httpx

        httpx_mock.add_exception(httpx.TimeoutException("Request timed out"))

        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
        )
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        # Request should succeed despite callback timeout
        response = await router.route("test prompt")
        assert response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_http_callback_network_error_does_not_break_request(
        self, httpx_mock: HTTPXMock
    ) -> None:
        """Test that HTTP callback network error doesn't break the request."""
        import httpx

        httpx_mock.add_exception(httpx.NetworkError("Connection failed"))

        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
        )
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        # Request should succeed despite callback network error
        response = await router.route("test prompt")
        assert response.startswith("Mock response to:")


class TestCallbackValidation:
    """Test callback configuration validation."""

    def test_cannot_specify_both_callbacks(self) -> None:
        """Test that ValueError is raised when both callbacks are specified."""
        async def dummy_callback(data: UsageData) -> None:
            pass

        with pytest.raises(ValueError, match="Cannot specify both"):
            Router(
                strategy="round-robin",
                usage_callback=dummy_callback,
                callback_url="https://api.example.com/usage",
            )

    def test_can_specify_only_python_callback(self) -> None:
        """Test that only Python callback can be specified."""
        async def dummy_callback(data: UsageData) -> None:
            pass

        router = Router(
            strategy="round-robin",
            usage_callback=dummy_callback,
        )
        assert router.usage_callback is not None
        assert router.callback_url is None

    def test_can_specify_only_http_callback(self) -> None:
        """Test that only HTTP callback can be specified."""
        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
        )
        assert router.callback_url is not None
        assert router.usage_callback is None

    def test_can_specify_tenant_id_with_http_callback(self) -> None:
        """Test that tenant_id can be specified with HTTP callback."""
        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
            tenant_id="tenant-123",
        )
        assert router.tenant_id == "tenant-123"

    def test_can_specify_platform_key_id_with_http_callback(self) -> None:
        """Test that platform_key_id can be specified with HTTP callback."""
        router = Router(
            strategy="round-robin",
            callback_url="https://api.example.com/usage",
            platform_key_id="key-456",
        )
        assert router.platform_key_id == "key-456"

