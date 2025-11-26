"""Unit tests for streaming functionality.

This module tests streaming support across all components:
- MockProvider.generate_stream()
- Router.route_stream()
- LangChain MultiLLMOrchestrator._stream() and _astream()
- Fallback behavior in streaming mode
- Parameter handling in streaming
"""

import pytest

from orchestrator import Router
from orchestrator.providers.base import (
    AuthenticationError,
    GenerationParams,
    InvalidRequestError,
    ProviderError,
    ProviderConfig,
    RateLimitError,
    TimeoutError,
)
from orchestrator.providers.mock import MockProvider


class TestMockProviderStreaming:
    """Test MockProvider.generate_stream() functionality."""

    @pytest.mark.asyncio
    async def test_mock_provider_streaming_normal_mode(self) -> None:
        """Test that mock-normal mode streams response word by word.

        Verifies that generate_stream() yields chunks that, when concatenated,
        match the result of generate() exactly.
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)

        # Get non-streaming result for comparison
        expected_response = await provider.generate("Hello, world!")

        # Stream and collect chunks
        chunks = []
        async for chunk in provider.generate_stream("Hello, world!"):
            chunks.append(chunk)

        # Concatenate chunks and compare
        streamed_response = "".join(chunks)
        assert streamed_response == expected_response
        assert len(chunks) > 0  # Should have multiple chunks (words)

    @pytest.mark.asyncio
    async def test_mock_provider_streaming_timeout_mode(self) -> None:
        """Test that mock-timeout mode raises TimeoutError immediately.

        Verifies that error modes raise exceptions before any chunks are yielded,
        allowing Router to fallback to another provider.
        """
        config = ProviderConfig(name="test", model="mock-timeout")
        provider = MockProvider(config)

        with pytest.raises(TimeoutError, match="Mock timeout simulation"):
            async for _ in provider.generate_stream("test"):
                # Should not reach here
                pytest.fail("Should have raised TimeoutError before yielding chunks")

    @pytest.mark.asyncio
    async def test_mock_provider_streaming_ratelimit_mode(self) -> None:
        """Test that mock-ratelimit mode raises RateLimitError immediately."""
        config = ProviderConfig(name="test", model="mock-ratelimit")
        provider = MockProvider(config)

        with pytest.raises(RateLimitError, match="Mock rate limit simulation"):
            async for _ in provider.generate_stream("test"):
                pytest.fail("Should have raised RateLimitError")

    @pytest.mark.asyncio
    async def test_mock_provider_streaming_auth_error_mode(self) -> None:
        """Test that mock-auth-error mode raises AuthenticationError immediately."""
        config = ProviderConfig(name="test", model="mock-auth-error")
        provider = MockProvider(config)

        with pytest.raises(AuthenticationError, match="Mock authentication failure"):
            async for _ in provider.generate_stream("test"):
                pytest.fail("Should have raised AuthenticationError")

    @pytest.mark.asyncio
    async def test_mock_provider_streaming_invalid_request_mode(self) -> None:
        """Test that mock-invalid-request mode raises InvalidRequestError immediately."""
        config = ProviderConfig(name="test", model="mock-invalid-request")
        provider = MockProvider(config)

        with pytest.raises(InvalidRequestError, match="Mock invalid request"):
            async for _ in provider.generate_stream("test"):
                pytest.fail("Should have raised InvalidRequestError")

    @pytest.mark.asyncio
    async def test_mock_provider_streaming_with_max_tokens(self) -> None:
        """Test that max_tokens is respected in streaming mode.

        Verifies that when max_tokens is specified, the concatenated streamed
        response matches the truncated result from generate().
        """
        config = ProviderConfig(name="test", model="mock-normal")
        provider = MockProvider(config)

        params = GenerationParams(max_tokens=10)

        # Get non-streaming result for comparison
        expected_response = await provider.generate("Hello, world!", params=params)

        # Stream and collect chunks
        chunks = []
        async for chunk in provider.generate_stream("Hello, world!", params=params):
            chunks.append(chunk)

        # Concatenate chunks and compare
        streamed_response = "".join(chunks)
        assert streamed_response == expected_response
        assert len(streamed_response) == 10  # Should be truncated to max_tokens


class TestRouterStreaming:
    """Test Router.route_stream() functionality."""

    @pytest.mark.asyncio
    async def test_router_streaming_single_provider(self) -> None:
        """Test that route_stream() works with a single provider.

        Verifies that route_stream() yields chunks that, when concatenated,
        match the result of route().
        """
        router = Router(strategy="round-robin")
        config = ProviderConfig(name="provider1", model="mock-normal")
        router.add_provider(MockProvider(config))

        # Get non-streaming result for comparison
        expected_response = await router.route("test prompt")

        # Stream and collect chunks
        chunks = []
        async for chunk in router.route_stream("test prompt"):
            chunks.append(chunk)

        # Concatenate chunks and compare
        streamed_response = "".join(chunks)
        assert streamed_response == expected_response

    @pytest.mark.asyncio
    async def test_router_streaming_fallback_before_first_chunk(self) -> None:
        """Test that fallback works when error occurs before first chunk.

        Verifies that when the first provider fails (before yielding any chunks),
        Router automatically falls back to the next provider and successfully streams.
        """
        router = Router(strategy="round-robin")

        # Add: timeout provider (will fail), then normal provider (will succeed)
        router.add_provider(
            MockProvider(ProviderConfig(name="p1", model="mock-timeout"))
        )
        router.add_provider(
            MockProvider(ProviderConfig(name="p2", model="mock-normal"))
        )

        # Should fallback from p1 (timeout) to p2 (success) and stream successfully
        chunks = []
        async for chunk in router.route_stream("test"):
            chunks.append(chunk)

        # Should have received chunks from p2
        assert len(chunks) > 0
        streamed_response = "".join(chunks)
        assert streamed_response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_router_streaming_fallback_tries_all_providers(self) -> None:
        """Test that fallback tries all providers in circular order.

        Verifies that when multiple providers fail, Router tries all providers
        before giving up.
        """
        router = Router(strategy="round-robin")

        # Add: timeout, timeout, normal
        router.add_provider(
            MockProvider(ProviderConfig(name="p1", model="mock-timeout"))
        )
        router.add_provider(
            MockProvider(ProviderConfig(name="p2", model="mock-timeout"))
        )
        router.add_provider(
            MockProvider(ProviderConfig(name="p3", model="mock-normal"))
        )

        # Should try p1 (timeout) → p2 (timeout) → p3 (success)
        chunks = []
        async for chunk in router.route_stream("test"):
            chunks.append(chunk)

        # Should have received chunks from p3
        assert len(chunks) > 0
        streamed_response = "".join(chunks)
        assert streamed_response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_router_streaming_all_providers_failed(self) -> None:
        """Test that route_stream() raises error when all providers fail.

        Verifies that when all providers fail before yielding any chunks,
        Router raises the last error encountered.
        """
        router = Router(strategy="round-robin")

        # Add 3 timeout providers (all will fail)
        for i in range(3):
            router.add_provider(
                MockProvider(ProviderConfig(name=f"p{i+1}", model="mock-timeout"))
            )

        # Should raise TimeoutError (last error)
        with pytest.raises(TimeoutError, match="Mock timeout simulation"):
            async for _ in router.route_stream("test"):
                pytest.fail("Should have raised TimeoutError")

    @pytest.mark.asyncio
    async def test_router_streaming_empty_providers_raises_error(self) -> None:
        """Test that route_stream() raises error when no providers registered."""
        router = Router(strategy="round-robin")

        with pytest.raises(ProviderError, match="No providers registered"):
            async for _ in router.route_stream("test"):
                pytest.fail("Should have raised ProviderError")

    @pytest.mark.asyncio
    async def test_router_streaming_with_params(self) -> None:
        """Test that GenerationParams are correctly passed through in streaming.

        Verifies that parameters like max_tokens are respected in streaming mode.
        """
        router = Router(strategy="round-robin")
        router.add_provider(
            MockProvider(ProviderConfig(name="p1", model="mock-normal"))
        )

        params = GenerationParams(max_tokens=15, temperature=0.8)

        # Stream and collect chunks
        chunks = []
        async for chunk in router.route_stream("test prompt", params=params):
            chunks.append(chunk)

        # Concatenate and verify max_tokens limit
        streamed_response = "".join(chunks)
        assert len(streamed_response) == 15  # Should be truncated to max_tokens


class TestLangChainStreaming:
    """Test LangChain streaming methods (_astream and _stream)."""

    @pytest.mark.asyncio
    async def test_langchain_astream(self) -> None:
        """Test that _astream() correctly streams responses.

        Verifies that _astream() yields chunks that, when concatenated,
        match the result of _acall().
        """
        pytest.importorskip("langchain_core")

        from orchestrator.langchain import LANGCHAIN_AVAILABLE, MultiLLMOrchestrator

        if not LANGCHAIN_AVAILABLE:
            pytest.skip("langchain-core is not available")

        router = Router(strategy="round-robin")
        config = ProviderConfig(name="mock", model="mock-normal")
        router.add_provider(MockProvider(config))

        llm = MultiLLMOrchestrator(router=router)

        # Get non-streaming result for comparison
        expected_response = await llm._acall("test prompt")

        # Stream and collect chunks
        chunks = []
        async for chunk in llm._astream("test prompt"):
            chunks.append(chunk)

        # Concatenate chunks and compare
        streamed_response = "".join(chunks)
        assert streamed_response == expected_response

    def test_langchain_stream_sync(self) -> None:
        """Test that _stream() correctly streams responses synchronously.

        Verifies that _stream() yields chunks that, when concatenated,
        match the result of _call().
        """
        pytest.importorskip("langchain_core")

        from orchestrator.langchain import LANGCHAIN_AVAILABLE, MultiLLMOrchestrator

        if not LANGCHAIN_AVAILABLE:
            pytest.skip("langchain-core is not available")

        router = Router(strategy="round-robin")
        config = ProviderConfig(name="mock", model="mock-normal")
        router.add_provider(MockProvider(config))

        llm = MultiLLMOrchestrator(router=router)

        # Get non-streaming result for comparison
        expected_response = llm._call("test prompt")

        # Stream and collect chunks
        chunks = []
        for chunk in llm._stream("test prompt"):
            chunks.append(chunk)

        # Concatenate chunks and compare
        streamed_response = "".join(chunks)
        assert streamed_response == expected_response

    @pytest.mark.asyncio
    async def test_langchain_astream_with_params(self) -> None:
        """Test that _astream() correctly handles parameters."""
        pytest.importorskip("langchain_core")

        from orchestrator.langchain import LANGCHAIN_AVAILABLE, MultiLLMOrchestrator

        if not LANGCHAIN_AVAILABLE:
            pytest.skip("langchain-core is not available")

        router = Router(strategy="round-robin")
        config = ProviderConfig(name="mock", model="mock-normal")
        router.add_provider(MockProvider(config))

        llm = MultiLLMOrchestrator(router=router)

        # Stream with parameters
        chunks = []
        async for chunk in llm._astream("test", max_tokens=12, temperature=0.9):
            chunks.append(chunk)

        # Verify max_tokens limit
        streamed_response = "".join(chunks)
        assert len(streamed_response) == 12

    def test_langchain_stream_sync_with_params(self) -> None:
        """Test that _stream() correctly handles parameters."""
        pytest.importorskip("langchain_core")

        from orchestrator.langchain import LANGCHAIN_AVAILABLE, MultiLLMOrchestrator

        if not LANGCHAIN_AVAILABLE:
            pytest.skip("langchain-core is not available")

        router = Router(strategy="round-robin")
        config = ProviderConfig(name="mock", model="mock-normal")
        router.add_provider(MockProvider(config))

        llm = MultiLLMOrchestrator(router=router)

        # Stream with parameters
        chunks = []
        for chunk in llm._stream("test", max_tokens=12, temperature=0.9):
            chunks.append(chunk)

        # Verify max_tokens limit
        streamed_response = "".join(chunks)
        assert len(streamed_response) == 12

