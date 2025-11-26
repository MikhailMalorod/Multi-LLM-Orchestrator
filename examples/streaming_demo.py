"""Basic streaming demo for Multi-LLM Orchestrator.

This example demonstrates how to use Router.route_stream() to stream
responses incrementally from LLM providers.

Example usage:
    python examples/streaming_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator import Router
from orchestrator.providers.base import ProviderConfig
from orchestrator.providers.mock import MockProvider


async def main() -> None:
    """Demonstrate streaming with Router and MockProvider."""
    print("=" * 60)
    print("Multi-LLM Orchestrator - Streaming Demo")
    print("=" * 60)
    print()

    # Create router with round-robin strategy
    router = Router(strategy="round-robin")

    # Add mock providers
    config1 = ProviderConfig(name="provider1", model="mock-normal")
    provider1 = MockProvider(config1)
    router.add_provider(provider1)

    config2 = ProviderConfig(name="provider2", model="mock-normal")
    provider2 = MockProvider(config2)
    router.add_provider(provider2)

    print("Router configured with 2 MockProvider instances")
    print()

    # Example 1: Basic streaming
    print("Example 1: Basic Streaming")
    print("-" * 60)
    prompt = "What is Python programming language?"
    print(f"Prompt: {prompt}")
    print("Streaming response:")
    print()

    async for chunk in router.route_stream(prompt):
        print(chunk, end="", flush=True)

    print()
    print()
    print()

    # Example 2: Streaming with parameters
    print("Example 2: Streaming with Parameters (max_tokens=20)")
    print("-" * 60)
    from orchestrator.providers.base import GenerationParams

    params = GenerationParams(max_tokens=20, temperature=0.8)
    prompt2 = "Explain machine learning in simple terms"
    print(f"Prompt: {prompt2}")
    print("Streaming response (truncated to 20 chars):")
    print()

    async for chunk in router.route_stream(prompt2, params=params):
        print(chunk, end="", flush=True)

    print()
    print()
    print()

    # Example 3: Fallback demonstration
    print("Example 3: Fallback in Streaming Mode")
    print("-" * 60)
    print("Creating router with timeout provider (will fail) and normal provider")
    router_fallback = Router(strategy="round-robin")

    # Add timeout provider (will fail before first chunk)
    timeout_config = ProviderConfig(name="timeout-provider", model="mock-timeout")
    router_fallback.add_provider(MockProvider(timeout_config))

    # Add normal provider (will succeed after fallback)
    normal_config = ProviderConfig(name="normal-provider", model="mock-normal")
    router_fallback.add_provider(MockProvider(normal_config))

    prompt3 = "Hello from fallback demo"
    print(f"Prompt: {prompt3}")
    print("Streaming (will fallback from timeout to normal):")
    print()

    async for chunk in router_fallback.route_stream(prompt3):
        print(chunk, end="", flush=True)

    print()
    print()
    print("=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

