"""Unit tests for Router.update_providers().

This module tests the update_providers() method functionality including:
- Basic provider update with metrics reset
- Preserving metrics for matching provider names
- Validation (empty list, duplicate names)
- Model change detection
- Prometheus integration
- Zero-downtime behavior
"""

import asyncio
import logging

import pytest

from orchestrator import Router
from orchestrator.providers.base import ProviderConfig
from orchestrator.providers.mock import MockProvider


class TestUpdateProvidersBasic:
    """Test basic update_providers() functionality."""

    @pytest.mark.asyncio
    async def test_update_providers_basic(self) -> None:
        """Test basic update with metrics reset (default)."""
        router = Router(strategy="round-robin")

        # Add initial providers
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p2", model="mock-normal")
        router.add_provider(MockProvider(config1))
        router.add_provider(MockProvider(config2))

        # Make some requests to accumulate metrics
        await router.route("test1")
        await router.route("test2")

        # Verify metrics exist and have data
        assert router.metrics["p1"].total_requests > 0
        assert router.metrics["p2"].total_requests > 0
        assert router._current_index > 0

        # Update with new provider list (only p1)
        new_config = ProviderConfig(name="p1-new", model="mock-normal")
        new_provider = MockProvider(new_config)
        await router.update_providers([new_provider])

        # Verify: new provider in list, old metrics removed, index reset
        assert len(router.providers) == 1
        assert router.providers[0].config.name == "p1-new"
        assert "p1-new" in router.metrics
        assert "p1" not in router.metrics
        assert "p2" not in router.metrics
        assert router.metrics["p1-new"].total_requests == 0  # Reset
        assert router._current_index == 0  # Reset

    @pytest.mark.asyncio
    async def test_update_providers_preserve_metrics(self) -> None:
        """Test preserving metrics for matching provider names."""
        router = Router(strategy="round-robin")

        # Add initial provider
        config1 = ProviderConfig(name="p1", model="mock-normal")
        router.add_provider(MockProvider(config1))

        # Make requests to accumulate metrics
        await router.route("test1")
        await router.route("test2")
        await router.route("test3")

        # Verify metrics exist
        original_requests = router.metrics["p1"].total_requests
        assert original_requests == 3

        # Update with new provider instance (same name)
        new_config = ProviderConfig(name="p1", model="mock-normal")
        new_provider = MockProvider(new_config)
        await router.update_providers([new_provider], preserve_metrics=True)

        # Verify: metrics preserved
        assert router.metrics["p1"].total_requests == original_requests
        assert len(router.providers) == 1
        assert router.providers[0].config.name == "p1"

    @pytest.mark.asyncio
    async def test_update_providers_preserve_metrics_removes_old(self) -> None:
        """Test that preserve_metrics removes metrics for providers not in new list."""
        router = Router(strategy="round-robin")

        # Add initial providers
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p2", model="mock-normal")
        router.add_provider(MockProvider(config1))
        router.add_provider(MockProvider(config2))

        # Make requests to accumulate metrics
        await router.route("test1")
        await router.route("test2")

        # Verify both have metrics
        assert "p1" in router.metrics
        assert "p2" in router.metrics

        # Update with only p1 (preserve metrics)
        new_config = ProviderConfig(name="p1", model="mock-normal")
        new_provider = MockProvider(new_config)
        await router.update_providers([new_provider], preserve_metrics=True)

        # Verify: p2 metrics removed, p1 metrics preserved
        assert "p1" in router.metrics
        assert "p2" not in router.metrics
        assert router.metrics["p1"].total_requests > 0  # Preserved


class TestUpdateProvidersValidation:
    """Test update_providers() validation."""

    @pytest.mark.asyncio
    async def test_update_providers_empty_raises(self) -> None:
        """Test that empty provider list raises ValueError."""
        router = Router(strategy="round-robin")

        # Add initial provider
        config = ProviderConfig(name="p1", model="mock-normal")
        router.add_provider(MockProvider(config))

        # Try to update with empty list
        with pytest.raises(ValueError, match="cannot be empty"):
            await router.update_providers([])

        # Verify original provider still exists
        assert len(router.providers) == 1

    @pytest.mark.asyncio
    async def test_update_providers_duplicate_names_raises(self) -> None:
        """Test that duplicate names in new_providers raises ValueError."""
        router = Router(strategy="round-robin")

        # Create two providers with same name
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p1", model="mock-normal")
        provider1 = MockProvider(config1)
        provider2 = MockProvider(config2)

        # Try to update with duplicate names
        with pytest.raises(ValueError, match="Duplicate provider names"):
            await router.update_providers([provider1, provider2])


class TestUpdateProvidersModelChange:
    """Test model change detection in update_providers()."""

    @pytest.mark.asyncio
    async def test_update_providers_model_change_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that model change is detected and logged as WARNING."""
        router = Router(strategy="round-robin")

        # Add initial provider with model-A
        config1 = ProviderConfig(name="p1", model="model-A")
        router.add_provider(MockProvider(config1))

        # Make some requests
        await router.route("test1")

        # Update with same name but different model
        new_config = ProviderConfig(name="p1", model="model-B")
        new_provider = MockProvider(new_config)

        with caplog.at_level(logging.WARNING):
            await router.update_providers([new_provider], preserve_metrics=True)

        # Verify WARNING was logged
        assert any(
            "model changed" in record.message and record.levelname == "WARNING"
            for record in caplog.records
        )

        # Verify metrics preserved despite model change
        assert router.metrics["p1"].total_requests > 0


class TestUpdateProvidersPrometheus:
    """Test update_providers() with Prometheus integration."""

    @pytest.mark.asyncio
    async def test_update_providers_prometheus_continues(self) -> None:
        """Test that Prometheus server continues running after update."""
        router = Router(strategy="round-robin")

        # Add initial providers
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p2", model="mock-normal")
        router.add_provider(MockProvider(config1))
        router.add_provider(MockProvider(config2))

        # Start metrics server
        await router.start_metrics_server(port=9091)  # Use different port to avoid conflicts

        try:
            # Make some requests
            await router.route("test1")
            await router.route("test2")

            # Update providers
            new_config = ProviderConfig(name="p3", model="mock-normal")
            new_provider = MockProvider(new_config)
            await router.update_providers([new_provider])

            # Verify: metrics server still running, new metrics exported
            assert router._prometheus_exporter is not None
            assert "p3" in router.metrics
            assert "p1" not in router.metrics
            assert "p2" not in router.metrics

            # Make request with new provider
            await router.route("test3")

            # Verify metrics updated
            assert router.metrics["p3"].total_requests > 0

        finally:
            # Cleanup
            await router.stop_metrics_server()


class TestUpdateProvidersZeroDowntime:
    """Test zero-downtime behavior of update_providers()."""

    @pytest.mark.asyncio
    async def test_update_providers_zero_downtime(self) -> None:
        """Test that active requests continue on old providers during update."""
        router = Router(strategy="round-robin")

        # Add initial providers
        config1 = ProviderConfig(name="p1", model="mock-normal")
        config2 = ProviderConfig(name="p2", model="mock-normal")
        router.add_provider(MockProvider(config1))
        router.add_provider(MockProvider(config2))

        # Start multiple concurrent requests
        async def make_request(request_id: int) -> str:
            return await router.route(f"test-{request_id}")

        # Start 5 concurrent requests
        tasks = [asyncio.create_task(make_request(i)) for i in range(5)]

        # Wait a bit to ensure some requests have started
        await asyncio.sleep(0.05)

        # Update providers while requests are in progress
        new_config = ProviderConfig(name="p3", model="mock-normal")
        new_provider = MockProvider(new_config)
        await router.update_providers([new_provider])

        # Wait for all active requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify: all active requests completed successfully
        assert len(results) == 5
        assert all(
            isinstance(r, str) and r.startswith("Mock response to:")
            for r in results
        )

        # Verify: new requests use new provider
        new_response = await router.route("new-request")
        assert new_response.startswith("Mock response to:")
        # New provider should be used (p3)
        assert "p3" in router.metrics
        assert router.metrics["p3"].total_requests > 0

