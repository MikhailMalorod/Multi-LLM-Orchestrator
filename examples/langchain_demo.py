#!/usr/bin/env python3
"""LangChain Integration Demo for Multi-LLM Orchestrator.

This demo script demonstrates how to use Multi-LLM Orchestrator providers
with LangChain chains, prompts, and other LangChain components.

The demo uses MockProvider to simulate LLM behavior without requiring
actual API credentials.

Usage:
    python examples/langchain_demo.py

Requirements:
    pip install multi-llm-orchestrator[langchain]
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from langchain_core.prompts import ChatPromptTemplate
except ImportError:
    print(
        "Error: langchain-core is required for this demo.\n"
        "Install with: pip install multi-llm-orchestrator[langchain]"
    )
    sys.exit(1)

from src.orchestrator import Router
from src.orchestrator.langchain import MultiLLMOrchestrator
from src.orchestrator.providers.base import ProviderConfig
from src.orchestrator.providers.mock import MockProvider


def main() -> None:
    """Main function demonstrating LangChain integration."""
    print("=" * 60)
    print("Multi-LLM Orchestrator: LangChain Integration Demo")
    print("=" * 60)
    print()

    # Create router with MockProvider
    print("1. Creating Router with MockProvider...")
    router = Router(strategy="round-robin")
    config = ProviderConfig(name="mock-provider", model="mock-normal")
    router.add_provider(MockProvider(config))
    print("   ✅ Router created with 1 provider")
    print()

    # Create LangChain-compatible LLM
    print("2. Creating MultiLLMOrchestrator (LangChain wrapper)...")
    llm = MultiLLMOrchestrator(router=router)
    print(f"   ✅ LLM type: {llm._llm_type}")
    print()

    # Direct LLM invocation
    print("3. Direct LLM invocation (synchronous)...")
    response = llm.invoke("What is Python?")
    print(f"   Response: {response}")
    print()

    # LangChain Chain with prompt template
    print("4. Using LangChain Chain with prompt template...")
    prompt = ChatPromptTemplate.from_template("Tell me about {topic}")
    chain = prompt | llm

    result = chain.invoke({"topic": "async programming"})
    print(f"   Response: {result.content}")
    print()

    # Multiple topics
    print("5. Processing multiple topics...")
    topics = ["machine learning", "web development", "data science"]
    for topic in topics:
        result = chain.invoke({"topic": topic})
        print(f"   {topic}: {result.content[:50]}...")
    print()

    print("=" * 60)
    print("✅ Demo completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  - Replace MockProvider with GigaChatProvider or YandexGPTProvider")
    print("  - Use different routing strategies (random, first-available)")
    print("  - Combine with other LangChain components (agents, tools, etc.)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

