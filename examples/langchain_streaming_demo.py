"""LangChain streaming demo for Multi-LLM Orchestrator.

This example demonstrates how to use MultiLLMOrchestrator with LangChain
for streaming text generation.

Prerequisites:
    pip install multi-llm-orchestrator[langchain]

Example usage:
    python examples/langchain_streaming_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from langchain_core.language_models.llms import BaseLLM
except ImportError:
    print(
        "Error: langchain-core is required for this demo.\n"
        "Install with: pip install multi-llm-orchestrator[langchain]"
    )
    sys.exit(1)

from orchestrator import Router
from orchestrator.langchain import MultiLLMOrchestrator
from orchestrator.providers.base import ProviderConfig
from orchestrator.providers.mock import MockProvider


async def async_streaming_example() -> None:
    """Demonstrate async streaming with _astream()."""
    print("=" * 60)
    print("LangChain Streaming Demo - Async (_astream)")
    print("=" * 60)
    print()

    # Create router with providers
    router = Router(strategy="round-robin")
    config = ProviderConfig(name="mock", model="mock-normal")
    router.add_provider(MockProvider(config))

    # Create LangChain wrapper
    llm = MultiLLMOrchestrator(router=router)

    print("Example: Async Streaming")
    print("-" * 60)
    prompt = "Explain what artificial intelligence is"
    print(f"Prompt: {prompt}")
    print("Streaming response (async):")
    print()

    # Stream asynchronously
    async for chunk in llm._astream(prompt):
        print(chunk, end="", flush=True)

    print()
    print()


def sync_streaming_example() -> None:
    """Demonstrate sync streaming with _stream()."""
    print("=" * 60)
    print("LangChain Streaming Demo - Sync (_stream)")
    print("=" * 60)
    print()

    # Create router with providers
    router = Router(strategy="round-robin")
    config = ProviderConfig(name="mock", model="mock-normal")
    router.add_provider(MockProvider(config))

    # Create LangChain wrapper
    llm = MultiLLMOrchestrator(router=router)

    print("Example: Sync Streaming")
    print("-" * 60)
    prompt = "What is machine learning?"
    print(f"Prompt: {prompt}")
    print("Streaming response (sync):")
    print()

    # Stream synchronously
    for chunk in llm._stream(prompt):
        print(chunk, end="", flush=True)

    print()
    print()


async def main() -> None:
    """Run all streaming examples."""
    # Async streaming
    await async_streaming_example()
    print()

    print("=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    # Run sync example separately (not from async context)
    print("=" * 60)
    print("LangChain Streaming Demo - Sync (_stream)")
    print("=" * 60)
    print()
    sync_streaming_example()
    print()

    # Run async examples
    asyncio.run(main())

