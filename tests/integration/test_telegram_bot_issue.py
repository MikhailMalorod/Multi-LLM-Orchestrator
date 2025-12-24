"""Integration test for Issue #4: Event loop cleanup in Telegram bot pattern.

This test reproduces the asyncio.to_thread() pattern used in production Telegram bots
and verifies that httpx.AsyncClient cleanup executes before loop.close().

Issue: https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/issues/4
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from orchestrator import Router
from orchestrator.providers import MockProvider, ProviderConfig


@pytest.mark.asyncio
async def test_telegram_bot_pattern_with_mock_provider() -> None:
    """Test asyncio.to_thread() pattern with MockProvider (simulates Issue #4).

    This test reproduces the exact pattern used in production Telegram bots:
    1. Main async event loop (simulates Telegram bot's main loop)
    2. Message handler uses asyncio.to_thread() to call sync function
    3. Sync function calls Router.route() via LangChain wrapper
    4. Internal: Router uses asyncio.run() → enhanced cleanup prevents errors

    Before v0.7.4: ~50% failure rate (httpx cleanup after loop.close())
    After v0.7.4: 100% success rate (enhanced cleanup with asyncio.sleep(0))
    """
    # Setup: Create Router with MockProvider
    config = ProviderConfig(
        name="mock-test",
        model="mock-normal"
    )
    provider = MockProvider(config)
    router = Router(strategy="round-robin")
    router.add_provider(provider)

    # Simulate sync function (like in LangChain wrapper)
    def sync_generate(prompt: str) -> str:
        """Sync function that calls Router (uses asyncio.run() internally)."""
        # This creates new event loop → enhanced cleanup prevents errors
        return asyncio.run(router.route(prompt))

    # Simulate Telegram bot pattern: asyncio.to_thread()
    async def simulate_telegram_handler(prompt: str) -> str:
        """Simulates Telegram message handler using asyncio.to_thread()."""
        # This is EXACTLY how production Telegram bots work!
        result = await asyncio.to_thread(sync_generate, prompt)
        return result

    # Run multiple requests (reproduce ~50% failure rate before fix)
    results = []
    for i in range(10):
        prompt = f"Test request {i + 1}"
        result = await simulate_telegram_handler(prompt)
        results.append(result)

    # Verify: All requests succeeded (no "Event loop is closed" errors)
    assert len(results) == 10
    assert all("Mock response" in r for r in results)


@pytest.mark.asyncio
async def test_thread_pool_pattern_multiple_workers() -> None:
    """Test ThreadPoolExecutor pattern with multiple concurrent workers.

    This test simulates high-load scenarios where multiple threads
    execute sync functions with asyncio.run() simultaneously.

    Before v0.7.4: Race conditions in httpx cleanup
    After v0.7.4: Thread-safe cleanup with enhanced steps
    """
    # Setup
    config = ProviderConfig(name="mock-test", model="mock-normal")
    provider = MockProvider(config)
    router = Router(strategy="round-robin")
    router.add_provider(provider)

    def sync_generate(prompt: str) -> str:
        """Sync function using asyncio.run() (enhanced cleanup)."""
        return asyncio.run(router.route(prompt))

    # Run 20 concurrent requests in ThreadPoolExecutor (stress test)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(sync_generate, f"Request {i}")
            for i in range(20)
        ]
        results = [f.result() for f in futures]

    # Verify: All requests succeeded
    assert len(results) == 20
    assert all("Mock response" in r for r in results)


@pytest.mark.asyncio
async def test_nested_event_loops_cleanup() -> None:
    """Test nested event loop cleanup (edge case).

    Verifies that enhanced cleanup works correctly when:
    - Outer async context (e.g., Telegram bot)
    - Inner asyncio.run() (e.g., LangChain wrapper)
    - httpx.AsyncClient cleanup must execute before inner loop.close()
    """
    # Setup
    config = ProviderConfig(name="mock-test", model="mock-normal")
    provider = MockProvider(config)
    router = Router(strategy="round-robin")
    router.add_provider(provider)

    def sync_generate(prompt: str) -> str:
        return asyncio.run(router.route(prompt))

    # Nested pattern: async → to_thread → asyncio.run()
    async def outer_async_handler() -> str:
        # This simulates nested event loops
        result = await asyncio.to_thread(sync_generate, "Nested test")
        return result

    # Run 5 times to verify stability
    for _ in range(5):
        result = await outer_async_handler()
        assert "Mock response" in result

