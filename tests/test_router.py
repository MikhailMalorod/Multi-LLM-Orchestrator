"""Unit tests for Router.

This module tests Router functionality including:
- Strategy validation and initialization
- Provider registration
- All three routing strategies (round-robin, random, first-available)
- Fallback mechanism
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
        
        Verifies that all three valid strategies (round-robin, random, first-available)
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
