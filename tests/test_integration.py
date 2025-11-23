"""Integration tests for Multi-LLM Orchestrator.

This module contains end-to-end integration tests that verify
Router and MockProvider work together correctly in realistic scenarios.
"""

import pytest

from orchestrator import Router
from orchestrator.providers.base import ProviderError, TimeoutError
from orchestrator.providers.mock import MockProvider
from orchestrator.providers.base import ProviderConfig


class TestIntegrationHappyPath:
    """Test happy path scenarios with Router and MockProvider."""

    @pytest.mark.asyncio
    async def test_integration_happy_path(self) -> None:
        """Test happy path: Router with 3 normal providers, 5 successful requests.
        
        Verifies that Router correctly routes requests to MockProvider instances
        and all requests complete successfully in a normal operation scenario.
        """
        router = Router(strategy="round-robin")
        
        # Add 3 normal providers
        for i in range(3):
            config = ProviderConfig(name=f"provider-{i+1}", model="mock-normal")
            router.add_provider(MockProvider(config))
        
        # Make 5 requests - all should succeed
        responses = []
        for i in range(5):
            response = await router.route(f"Request {i+1}")
            responses.append(response)
        
        # Verify all responses are valid
        assert len(responses) == 5
        assert all(r.startswith("Mock response to:") for r in responses)
        assert all("Request" in r for i, r in enumerate(responses))


class TestIntegrationFallback:
    """Test fallback scenarios with Router and MockProvider."""

    @pytest.mark.asyncio
    async def test_integration_fallback_scenario(self) -> None:
        """Test fallback: Router with [timeout, normal, normal], fallback to second.
        
        Verifies that Router correctly handles fallback when the first provider
        fails (timeout) and automatically switches to the next available provider.
        """
        router = Router(strategy="round-robin")
        
        # Add: timeout, normal, normal
        router.add_provider(MockProvider(ProviderConfig(name="p1", model="mock-timeout")))
        router.add_provider(MockProvider(ProviderConfig(name="p2", model="mock-normal")))
        router.add_provider(MockProvider(ProviderConfig(name="p3", model="mock-normal")))
        
        # Make 1 request - should fallback from p1 (timeout) to p2 (success)
        response = await router.route("test prompt")
        
        # Verify successful response after fallback
        assert response.startswith("Mock response to:")
        assert "test prompt" in response


class TestIntegrationAllFailed:
    """Test error handling when all providers fail."""

    @pytest.mark.asyncio
    async def test_integration_all_failed(self) -> None:
        """Test error handling: Router with [timeout, timeout, timeout], raises error.
        
        Verifies that Router correctly handles the scenario when all providers fail
        and raises the last exception encountered (TimeoutError).
        """
        router = Router(strategy="round-robin")
        
        # Add 3 timeout providers (all will fail)
        for i in range(3):
            router.add_provider(
                MockProvider(ProviderConfig(name=f"p{i+1}", model="mock-timeout"))
            )
        
        # Should raise TimeoutError (last error from all failed providers)
        with pytest.raises(TimeoutError, match="Mock timeout simulation"):
            await router.route("test prompt")

