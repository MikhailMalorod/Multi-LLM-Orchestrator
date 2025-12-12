"""Cost estimation for LLM providers.

This module provides centralized pricing configuration and cost calculation
for different LLM providers based on token usage.

Pricing is specified in RUB (Russian Rubles) per 1000 tokens with unified
pricing (no separation between prompt and completion tokens).

Example:
    ```python
    from orchestrator.pricing import calculate_cost, get_price_per_1k

    # Calculate cost for GigaChat-Pro
    cost = calculate_cost("gigachat", "GigaChat-Pro", 1500)
    print(cost)  # 3.0 RUB (1500 tokens * 2.00 / 1000)

    # Get price per 1000 tokens
    price = get_price_per_1k("yandexgpt", "yandexgpt/latest")
    print(price)  # 1.50
    ```
"""

import logging

logger = logging.getLogger("orchestrator.pricing")

# Pricing in RUB per 1000 tokens (unified, no prompt/completion split)
# Format: {provider_name: {model_name: price_per_1k_tokens, "default": default_price}}
PRICING: dict[str, dict[str, float]] = {
    "gigachat": {
        "GigaChat": 1.00,
        "GigaChat-Pro": 2.00,
        "GigaChat-Plus": 1.50,
        "default": 1.50,
    },
    "yandexgpt": {
        "yandexgpt/latest": 1.50,
        "yandexgpt-lite/latest": 0.75,
        "default": 1.50,
    },
    "ollama": {
        "default": 0.0,
    },
    "mock": {
        "default": 0.0,
    },
}


def calculate_cost(
    provider_name: str, model: str | None, total_tokens: int
) -> float:
    """Calculate cost in RUB for LLM request.

    This function calculates the cost based on the provider, model, and
    total token count. Pricing is unified (no separation between prompt
    and completion tokens).

    Args:
        provider_name: Provider name (e.g., "gigachat", "yandexgpt").
                      Case-insensitive.
        model: Model name (e.g., "GigaChat-Pro", "yandexgpt/latest").
              If None or unknown, uses default price for provider.
        total_tokens: Total token count (prompt + completion)

    Returns:
        Cost in rubles as float (unrounded for precision).
        Returns 0.0 for unknown providers or free providers (Ollama, Mock).

    Example:
        ```python
        # GigaChat-Pro pricing
        cost = calculate_cost("gigachat", "GigaChat-Pro", 1500)
        # Returns: 3.0 (1500 tokens * 2.00 RUB / 1000)

        # YandexGPT lite pricing
        cost = calculate_cost("yandexgpt", "yandexgpt-lite/latest", 2000)
        # Returns: 1.5 (2000 tokens * 0.75 RUB / 1000)

        # Free provider
        cost = calculate_cost("ollama", "llama2", 1000)
        # Returns: 0.0

        # Unknown provider
        cost = calculate_cost("unknown-provider", "some-model", 1000)
        # Returns: 0.0 (with warning log)
        ```

    Note:
        - Provider name is case-insensitive ("GigaChat" == "gigachat")
        - Unknown models use provider's default price (with warning)
        - Unknown providers return 0.0 cost (with warning)
    """
    # Normalize provider name to lowercase for lookup
    provider_key = provider_name.lower()

    # Get provider pricing config
    provider_pricing = PRICING.get(provider_key)

    # If not found directly, check if it's a variant (e.g., "mock-1" → "mock")
    if not provider_pricing:
        # Try to match by prefix (e.g., "mock-1" → "mock", "gigachat-dev" → "gigachat")
        for known_provider in PRICING.keys():
            if provider_key.startswith(known_provider):
                provider_pricing = PRICING[known_provider]
                break

    if not provider_pricing:
        logger.warning(
            f"Unknown provider '{provider_name}', assuming zero cost. "
            f"Available providers: {list(PRICING.keys())}"
        )
        return 0.0

    # Get model-specific price or default
    price_per_1k = provider_pricing.get(model or "default")
    if price_per_1k is None:
        # Model not found, use provider default
        price_per_1k = provider_pricing.get("default", 0.0)
        logger.warning(
            f"Unknown model '{model}' for provider '{provider_name}', "
            f"using default price: {price_per_1k} RUB/1K tokens"
        )

    # Calculate cost: (tokens / 1000) * price_per_1k
    cost = (total_tokens / 1000.0) * price_per_1k
    return cost


def get_price_per_1k(provider_name: str, model: str | None) -> float:
    """Get price per 1000 tokens for a provider/model combination.

    This is a convenience function to retrieve pricing without calculating
    cost for a specific token count.

    Args:
        provider_name: Provider name (case-insensitive)
        model: Model name (optional, uses default if None)

    Returns:
        Price per 1000 tokens in RUB.
        Returns 0.0 for unknown providers.

    Example:
        ```python
        # Get GigaChat-Pro price
        price = get_price_per_1k("gigachat", "GigaChat-Pro")
        # Returns: 2.0

        # Get default price for provider
        price = get_price_per_1k("yandexgpt", None)
        # Returns: 1.50 (default for yandexgpt)

        # Unknown provider
        price = get_price_per_1k("unknown", "model")
        # Returns: 0.0
        ```
    """
    provider_key = provider_name.lower()
    provider_pricing = PRICING.get(provider_key, {})
    return provider_pricing.get(
        model or "default", provider_pricing.get("default", 0.0)
    )

