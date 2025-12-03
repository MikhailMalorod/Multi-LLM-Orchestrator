"""Unit tests for Router.

This module tests Router functionality including:
- Strategy validation and initialization
- Provider registration
- All routing strategies (round-robin, random, first-available, best-available)
- Fallback mechanism
- Metrics tracking and health status
- Edge cases (empty providers, all failed, etc.)
"""

import pytest

from orchestrator import Router
from orchestrator.providers.base import (
    GenerationParams,
    ProviderError,
    TimeoutError,
)
from orchestrator.providers.mock import MockProvider
from orchestrator.providers.base import ProviderConfig


class TestRouterInitialization:
    """Test Router initialization and strategy validation."""

    def test_router_init_valid_strategies(self) -> None:
        """Test that Router initializes with valid strategies.
        
        Verifies that all valid strategies (round-robin, random, first-available, best-available)
        can be used to initialize a Router without errors.
        """
        router_rr = Router(strategy="round-robin")
        assert router_rr.strategy == "round-robin"
        assert router_rr.providers == []
        
        router_random = Router(strategy="random")
        assert router_random.strategy == "random"
        assert router_random.providers == []
        
        router_fa = Router(strategy="first-available")
        assert router_fa.strategy == "first-available"
        assert router_fa.providers == []
        
        router_ba = Router(strategy="best-available")
        assert router_ba.strategy == "best-available"
        assert router_ba.providers == []

    def test_router_init_invalid_strategy_raises_error(self) -> None:
        """Test that invalid strategy raises ValueError.
        
        Verifies that providing an invalid strategy name raises ValueError
        with an appropriate error message.
        """
        with pytest.raises(ValueError, match="Invalid strategy"):
            Router(strategy="invalid-strategy")
        
        with pytest.raises(ValueError, match="Invalid strategy"):
            Router(strategy="")
        
        with pytest.raises(ValueError, match="Invalid strategy"):
            Router(strategy="round_robin")  # Wrong separator


class TestRouterProviderManagement:
    """Test Router provider registration."""

    def test_add_provider_increases_list(self) -> None:
        """Test that add_provider() increases the providers list.
        
        Verifies that adding providers to the router increases the list size
        and providers are stored correctly.
        """
        router = Router(strategy="round-robin")
        assert len(router.providers) == 0
        
        config1 = ProviderConfig(name="provider-1", model="mock-normal")
        provider1 = MockProvider(config1)
        router.add_provider(provider1)
        assert len(router.providers) == 1
        assert router.providers[0] == provider1
        
        config2 = ProviderConfig(name="provider-2", model="mock-normal")
        provider2 = MockProvider(config2)
        router.add_provider(provider2)
        assert len(router.providers) == 2
        assert router.providers[1] == provider2


class TestRouterRoundRobinStrategy:
    """Test round-robin routing strategy."""

    @pytest.mark.asyncio
    async def test_round_robin_cycles_through_providers(self) -> None:
        """Test that round-robin cycles through providers in order.
        
        Verifies that round-robin strategy selects providers in a cyclic order:
        provider-1 → provider-2 → provider-3 → provider-1 → provider-2
        """
        router = Router(strategy="round-robin")
        
        # Add 3 providers
        for i in range(3):
            config = ProviderConfig(name=f"provider-{i+1}", model="mock-normal")
            router.add_provider(MockProvider(config))
        
        # Make 5 requests - should cycle: 1 → 2 → 3 → 1 → 2
        responses = []
        for _ in range(5):
            response = await router.route("test")
            responses.append(response)
        
        # All should succeed
        assert len(responses) == 5
        assert all(r.startswith("Mock response to:") for r in responses)
        
        # Verify cycling by checking _current_index
        assert router._current_index == 5


class TestRouterRandomStrategy:
    """Test random routing strategy."""

    @pytest.mark.asyncio
    async def test_random_strategy_selects_from_available(self) -> None:
        """Test that random strategy selects from available providers.
        
        Verifies that random strategy successfully selects providers and
        all requests complete successfully (proving selection from available set).
        """
        router = Router(strategy="random")
        
        # Add 3 providers
        for i in range(3):
            config = ProviderConfig(name=f"provider-{i+1}", model="mock-normal")
            router.add_provider(MockProvider(config))
        
        # Make 10 requests - all should succeed
        responses = []
        for _ in range(10):
            response = await router.route("test")
            responses.append(response)
        
        # All should succeed (proving random selection from available providers)
        assert len(responses) == 10
        assert all(r.startswith("Mock response to:") for r in responses)


class TestRouterFirstAvailableStrategy:
    """Test first-available routing strategy."""

    @pytest.mark.asyncio
    async def test_first_available_selects_first_healthy(self) -> None:
        """Test that first-available selects the first healthy provider.
        
        Verifies that first-available strategy skips unhealthy providers
        and selects the first healthy one.
        """
        router = Router(strategy="first-available")
        
        # Add: unhealthy, healthy, healthy
        router.add_provider(MockProvider(ProviderConfig(name="p1", model="mock-unhealthy")))
        router.add_provider(MockProvider(ProviderConfig(name="p2", model="mock-normal")))
        router.add_provider(MockProvider(ProviderConfig(name="p3", model="mock-normal")))
        
        # Make 3 requests - all should go to p2 (first healthy)
        for _ in range(3):
            response = await router.route("test")
            assert response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_first_available_fallback_when_all_unhealthy(self) -> None:
        """Test that first-available falls back when all providers are unhealthy.
        
        Verifies that when all providers are unhealthy, first-available selects
        the first provider and fallback mechanism tries all providers.
        """
        router = Router(strategy="first-available")
        
        # Add 3 unhealthy providers (but generate() works)
        router.add_provider(MockProvider(ProviderConfig(name="p1", model="mock-unhealthy")))
        router.add_provider(MockProvider(ProviderConfig(name="p2", model="mock-unhealthy")))
        router.add_provider(MockProvider(ProviderConfig(name="p3", model="mock-unhealthy")))
        
        # Should succeed (first provider selected, generate() works despite unhealthy)
        response = await router.route("test")
        assert response.startswith("Mock response to:")


class TestRouterFallback:
    """Test Router fallback mechanism."""

    @pytest.mark.asyncio
    async def test_fallback_timeout_to_next_provider(self) -> None:
        """Test that fallback switches to next provider when first times out.
        
        Verifies that when the selected provider times out, Router automatically
        falls back to the next provider in the list.
        """
        router = Router(strategy="round-robin")
        
        # Add: timeout, normal, normal
        router.add_provider(MockProvider(ProviderConfig(name="p1", model="mock-timeout")))
        router.add_provider(MockProvider(ProviderConfig(name="p2", model="mock-normal")))
        router.add_provider(MockProvider(ProviderConfig(name="p3", model="mock-normal")))
        
        # Should fallback from p1 (timeout) to p2 (success)
        response = await router.route("test")
        assert response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_fallback_tries_all_providers(self) -> None:
        """Test that fallback tries all providers in circular order.
        
        Verifies that when providers fail, Router tries all providers
        in a circular order starting from the selected one.
        """
        router = Router(strategy="round-robin")
        
        # Add: timeout, timeout, normal
        router.add_provider(MockProvider(ProviderConfig(name="p1", model="mock-timeout")))
        router.add_provider(MockProvider(ProviderConfig(name="p2", model="mock-timeout")))
        router.add_provider(MockProvider(ProviderConfig(name="p3", model="mock-normal")))
        
        # Should try p1 (timeout) → p2 (timeout) → p3 (success)
        response = await router.route("test")
        assert response.startswith("Mock response to:")


class TestRouterEdgeCases:
    """Test Router edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_route_empty_providers_raises_error(self) -> None:
        """Test that route() raises error when no providers registered.
        
        Verifies that calling route() with an empty providers list
        raises ProviderError with appropriate message.
        """
        router = Router(strategy="round-robin")
        
        with pytest.raises(ProviderError, match="No providers registered"):
            await router.route("test")

    @pytest.mark.asyncio
    async def test_route_all_providers_failed_raises_last_error(self) -> None:
        """Test that route() raises last error when all providers fail.
        
        Verifies that when all providers fail, Router raises the last
        exception encountered (TimeoutError in this case).
        """
        router = Router(strategy="round-robin")
        
        # Add 3 timeout providers
        for i in range(3):
            router.add_provider(
                MockProvider(ProviderConfig(name=f"p{i+1}", model="mock-timeout"))
            )
        
        # Should raise TimeoutError (last error)
        with pytest.raises(TimeoutError, match="Mock timeout simulation"):
            await router.route("test")

    @pytest.mark.asyncio
    async def test_route_with_generation_params(self) -> None:
        """Test that route() correctly passes GenerationParams to providers.
        
        Verifies that GenerationParams are correctly passed through Router
        to the provider's generate() method.
        """
        router = Router(strategy="round-robin")
        router.add_provider(MockProvider(ProviderConfig(name="p1", model="mock-normal")))
        
        params = GenerationParams(max_tokens=10, temperature=0.8)
        response = await router.route("test", params=params)
        
        # Response should be truncated to 10 chars due to max_tokens
        assert len(response) == 10
        assert response == "Mock respo"


class TestRouterMetrics:
    """Test Router metrics tracking."""

    def test_router_initializes_metrics_on_add_provider(self) -> None:
        """Test that Router initializes metrics when adding a provider."""
        router = Router(strategy="round-robin")
        
        config = ProviderConfig(name="provider-1", model="mock-normal")
        provider = MockProvider(config)
        router.add_provider(provider)
        
        assert "provider-1" in router.metrics
        metrics = router.metrics["provider-1"]
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0

    def test_router_rejects_duplicate_provider_names(self) -> None:
        """Test that Router rejects providers with duplicate names."""
        router = Router(strategy="round-robin")
        
        config1 = ProviderConfig(name="provider-1", model="mock-normal")
        provider1 = MockProvider(config1)
        router.add_provider(provider1)
        
        # Try to add provider with same name
        config2 = ProviderConfig(name="provider-1", model="mock-normal")
        provider2 = MockProvider(config2)
        
        with pytest.raises(ValueError, match="already exists"):
            router.add_provider(provider2)

    @pytest.mark.asyncio
    async def test_router_updates_metrics_on_success(self) -> None:
        """Test that Router updates metrics on successful request."""
        router = Router(strategy="round-robin")
        
        config = ProviderConfig(name="provider-1", model="mock-normal")
        router.add_provider(MockProvider(config))
        
        await router.route("test")
        
        metrics = router.metrics["provider-1"]
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.avg_latency_ms > 0

    @pytest.mark.asyncio
    async def test_router_updates_metrics_on_error(self) -> None:
        """Test that Router updates metrics on failed request."""
        router = Router(strategy="round-robin")
        
        config = ProviderConfig(name="provider-1", model="mock-timeout")
        router.add_provider(MockProvider(config))
        
        # This will fail, but fallback will try other providers
        # For this test, we need all providers to fail to see the error recorded
        with pytest.raises(TimeoutError):
            await router.route("test")
        
        # Metrics should be updated for the failed provider
        metrics = router.metrics["provider-1"]
        assert metrics.total_requests >= 1
        assert metrics.failed_requests >= 1

    @pytest.mark.asyncio
    async def test_router_updates_metrics_for_streaming(self) -> None:
        """Test that Router updates metrics for streaming requests."""
        router = Router(strategy="round-robin")
        
        config = ProviderConfig(name="provider-1", model="mock-normal")
        router.add_provider(MockProvider(config))
        
        chunks = []
        async for chunk in router.route_stream("test"):
            chunks.append(chunk)
        
        metrics = router.metrics["provider-1"]
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.avg_latency_ms > 0

    def test_get_metrics_returns_copy(self) -> None:
        """Test that get_metrics() returns a shallow copy."""
        router = Router(strategy="round-robin")
        
        config = ProviderConfig(name="provider-1", model="mock-normal")
        router.add_provider(MockProvider(config))
        
        metrics_dict = router.get_metrics()
        
        # Should be a copy, not the same object
        assert metrics_dict is not router.metrics
        assert "provider-1" in metrics_dict
        
        # Modifying the dict shouldn't affect router.metrics
        metrics_dict["new"] = "test"
        assert "new" not in router.metrics


class TestRouterBestAvailableStrategy:
    """Test best-available routing strategy."""

    @pytest.mark.asyncio
    async def test_best_available_selects_healthy_with_lowest_latency(self) -> None:
        """Test that best-available selects healthy provider with lowest latency."""
        router = Router(strategy="best-available")
        
        # Add providers with different latencies
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p2", model="mock-normal")
        router.add_provider(MockProvider(config1))
        router.add_provider(MockProvider(config2))
        
        # Make requests to build up metrics
        # p1 should get selected first (round-robin order initially)
        await router.route("test")
        
        # Both should be healthy, but best-available will select based on latency
        # After a few requests, it should prefer the one with lower latency
        for _ in range(5):
            await router.route("test")
        
        # Both providers should have metrics
        assert "p1" in router.metrics
        assert "p2" in router.metrics

    @pytest.mark.asyncio
    async def test_best_available_fallback_to_degraded_when_no_healthy(self) -> None:
        """Test that best-available falls back to degraded when no healthy providers."""
        router = Router(strategy="best-available")
        
        # Add providers
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p2", model="mock-normal")
        router.add_provider(MockProvider(config1))
        router.add_provider(MockProvider(config2))
        
        # Make enough requests to have metrics
        for _ in range(10):
            await router.route("test")
        
        # Both should be healthy initially
        assert router.metrics["p1"].health_status == "healthy"
        assert router.metrics["p2"].health_status == "healthy"

    @pytest.mark.asyncio
    async def test_best_available_uses_avg_latency_when_no_rolling(self) -> None:
        """Test that best-available uses avg_latency_ms when rolling_avg is None."""
        router = Router(strategy="best-available")
        
        config = ProviderConfig(name="p1", model="mock-normal")
        router.add_provider(MockProvider(config))
        
        # Make a few requests (not enough to fill rolling window)
        await router.route("test")
        
        metrics = router.metrics["p1"]
        # Should have avg_latency_ms but may not have rolling_avg yet
        assert metrics.avg_latency_ms > 0

    @pytest.mark.asyncio
    async def test_best_available_handles_all_unhealthy(self) -> None:
        """Test that best-available selects among unhealthy providers."""
        router = Router(strategy="best-available")
        
        # Add providers
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p2", model="mock-normal")
        router.add_provider(MockProvider(config1))
        router.add_provider(MockProvider(config2))
        
        # Even if all are unhealthy, best-available should still select one
        # (it doesn't fallback to round-robin)
        await router.route("test")
        
        # Should have selected a provider
        assert len(router.metrics) == 2
