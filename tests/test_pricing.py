"""Unit tests for pricing module.

This module tests cost calculation functionality including:
- Cost calculation for different providers and models
- Handling of unknown providers and models
- Default pricing fallback
- Free providers (Ollama, Mock)
"""

import pytest
from orchestrator.pricing import calculate_cost, get_price_per_1k, PRICING


class TestCalculateCost:
    """Test calculate_cost() function."""

    def test_calculate_cost_gigachat_base(self) -> None:
        """Test cost calculation for GigaChat base model."""
        cost = calculate_cost("gigachat", "GigaChat", 1000)
        assert cost == pytest.approx(1.00)

    def test_calculate_cost_gigachat_pro(self) -> None:
        """Test cost calculation for GigaChat-Pro model."""
        cost = calculate_cost("gigachat", "GigaChat-Pro", 1000)
        assert cost == pytest.approx(2.00)

    def test_calculate_cost_gigachat_plus(self) -> None:
        """Test cost calculation for GigaChat-Plus model."""
        cost = calculate_cost("gigachat", "GigaChat-Plus", 1000)
        assert cost == pytest.approx(1.50)

    def test_calculate_cost_yandexgpt_latest(self) -> None:
        """Test cost calculation for YandexGPT latest model."""
        cost = calculate_cost("yandexgpt", "yandexgpt/latest", 1000)
        assert cost == pytest.approx(1.50)

    def test_calculate_cost_yandexgpt_lite(self) -> None:
        """Test cost calculation for YandexGPT lite model."""
        cost = calculate_cost("yandexgpt", "yandexgpt-lite/latest", 1000)
        assert cost == pytest.approx(0.75)

    def test_calculate_cost_free_providers_ollama(self) -> None:
        """Test cost calculation for free provider (Ollama)."""
        cost = calculate_cost("ollama", "llama2", 1000)
        assert cost == 0.0

    def test_calculate_cost_free_providers_mock(self) -> None:
        """Test cost calculation for free provider (Mock)."""
        cost = calculate_cost("mock", "mock-normal", 1000)
        assert cost == 0.0

    def test_calculate_cost_unknown_provider(self) -> None:
        """Test cost calculation for unknown provider returns 0.0."""
        cost = calculate_cost("unknown-provider", "unknown-model", 1000)
        assert cost == 0.0

    def test_calculate_cost_unknown_model_uses_default_gigachat(self) -> None:
        """Test that unknown GigaChat model uses default price."""
        cost = calculate_cost("gigachat", "GigaChat-Ultra-New", 1000)
        assert cost == pytest.approx(1.50)  # default for gigachat

    def test_calculate_cost_unknown_model_uses_default_yandexgpt(self) -> None:
        """Test that unknown YandexGPT model uses default price."""
        cost = calculate_cost("yandexgpt", "yandexgpt-experimental", 1000)
        assert cost == pytest.approx(1.50)  # default for yandexgpt

    def test_calculate_cost_fractional_tokens(self) -> None:
        """Test cost calculation with fractional token counts."""
        # 1500 tokens * 2.00 RUB/1K = 3.0 RUB
        cost = calculate_cost("gigachat", "GigaChat-Pro", 1500)
        assert cost == pytest.approx(3.0)

        # 750 tokens * 0.75 RUB/1K = 0.5625 RUB
        cost = calculate_cost("yandexgpt", "yandexgpt-lite/latest", 750)
        assert cost == pytest.approx(0.5625)

    def test_calculate_cost_zero_tokens(self) -> None:
        """Test cost calculation with zero tokens."""
        cost = calculate_cost("gigachat", "GigaChat-Pro", 0)
        assert cost == 0.0

    def test_calculate_cost_large_token_count(self) -> None:
        """Test cost calculation with large token count."""
        # 100,000 tokens * 2.00 RUB/1K = 200.0 RUB
        cost = calculate_cost("gigachat", "GigaChat-Pro", 100000)
        assert cost == pytest.approx(200.0)

    def test_calculate_cost_case_insensitive_provider(self) -> None:
        """Test that provider name is case-insensitive."""
        cost1 = calculate_cost("gigachat", "GigaChat", 1000)
        cost2 = calculate_cost("GigaChat", "GigaChat", 1000)
        cost3 = calculate_cost("GIGACHAT", "GigaChat", 1000)
        assert cost1 == cost2 == cost3 == pytest.approx(1.00)

    def test_calculate_cost_none_model_uses_default(self) -> None:
        """Test that None model uses default price."""
        cost = calculate_cost("gigachat", None, 1000)
        assert cost == pytest.approx(1.50)  # default for gigachat

    def test_calculate_cost_provider_with_suffix(self) -> None:
        """Test that provider variants (e.g., mock-1, mock-2) match base provider."""
        # Test mock-1, mock-2, mock-3 all use "mock" pricing
        cost1 = calculate_cost("mock-1", "mock-normal", 1000)
        cost2 = calculate_cost("mock-2", "mock-normal", 1000)
        cost3 = calculate_cost("mock-3", "mock-normal", 1000)
        assert cost1 == 0.0  # mock is free
        assert cost2 == 0.0
        assert cost3 == 0.0

        # Test gigachat-dev uses gigachat pricing
        cost_dev = calculate_cost("gigachat-dev", "GigaChat-Pro", 1000)
        assert cost_dev == pytest.approx(2.00)  # GigaChat-Pro pricing


class TestGetPricePer1k:
    """Test get_price_per_1k() function."""

    def test_get_price_gigachat_pro(self) -> None:
        """Test getting price for GigaChat-Pro."""
        price = get_price_per_1k("gigachat", "GigaChat-Pro")
        assert price == pytest.approx(2.00)

    def test_get_price_yandexgpt_lite(self) -> None:
        """Test getting price for YandexGPT lite."""
        price = get_price_per_1k("yandexgpt", "yandexgpt-lite/latest")
        assert price == pytest.approx(0.75)

    def test_get_price_default_with_none_model(self) -> None:
        """Test getting default price when model is None."""
        price = get_price_per_1k("gigachat", None)
        assert price == pytest.approx(1.50)  # default for gigachat

    def test_get_price_unknown_provider(self) -> None:
        """Test getting price for unknown provider returns 0.0."""
        price = get_price_per_1k("unknown-provider", "some-model")
        assert price == 0.0

    def test_get_price_unknown_model_returns_default(self) -> None:
        """Test that unknown model returns provider default."""
        price = get_price_per_1k("gigachat", "unknown-model")
        assert price == pytest.approx(1.50)  # default for gigachat

    def test_get_price_free_provider(self) -> None:
        """Test getting price for free provider."""
        price = get_price_per_1k("ollama", "llama2")
        assert price == 0.0


class TestPricingTable:
    """Test PRICING configuration table."""

    def test_pricing_table_structure(self) -> None:
        """Test that PRICING table has expected structure."""
        assert isinstance(PRICING, dict)
        assert "gigachat" in PRICING
        assert "yandexgpt" in PRICING
        assert "ollama" in PRICING
        assert "mock" in PRICING

    def test_pricing_all_providers_have_default(self) -> None:
        """Test that all providers have default price."""
        for provider, pricing in PRICING.items():
            assert "default" in pricing, f"Provider {provider} missing 'default' price"

    def test_pricing_all_values_are_numeric(self) -> None:
        """Test that all pricing values are numeric."""
        for provider, pricing in PRICING.items():
            for model, price in pricing.items():
                assert isinstance(
                    price, (int, float)
                ), f"Price for {provider}/{model} is not numeric: {price}"
                assert (
                    price >= 0.0
                ), f"Price for {provider}/{model} is negative: {price}"

