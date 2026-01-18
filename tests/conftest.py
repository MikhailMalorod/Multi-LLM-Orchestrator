"""Pytest fixtures for Multi-LLM Orchestrator tests.

This module provides reusable fixtures for testing Router, MockProvider,
and related components. All fixtures follow pytest conventions and
support async testing with pytest-asyncio.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator import Router
from orchestrator.providers.base import ProviderConfig
from orchestrator.providers.mock import MockProvider


@pytest.fixture
def mock_provider_config() -> ProviderConfig:
    """Create a default ProviderConfig for testing.
    
    Returns:
        ProviderConfig instance with name="test-provider" and model="mock-normal"
    """
    return ProviderConfig(name="test-provider", model="mock-normal")


@pytest.fixture
def mock_provider_normal() -> MockProvider:
    """Create a MockProvider in normal mode.
    
    This provider will return successful responses with a 0.1s delay.
    
    Returns:
        MockProvider instance configured for normal operation
    """
    config = ProviderConfig(name="normal-provider", model="mock-normal")
    return MockProvider(config)


@pytest.fixture
def mock_provider_timeout() -> MockProvider:
    """Create a MockProvider in timeout mode.
    
    This provider will raise TimeoutError when generate() is called.
    
    Returns:
        MockProvider instance configured to simulate timeouts
    """
    config = ProviderConfig(name="timeout-provider", model="mock-timeout")
    return MockProvider(config)


@pytest.fixture
def mock_provider_unhealthy() -> MockProvider:
    """Create a MockProvider in unhealthy mode.
    
    This provider will return False for health_check() but generate() works normally.
    
    Returns:
        MockProvider instance configured as unhealthy
    """
    config = ProviderConfig(name="unhealthy-provider", model="mock-unhealthy")
    return MockProvider(config)


@pytest.fixture
def router_round_robin() -> Router:
    """Create a Router with round-robin strategy.
    
    Returns:
        Router instance configured for round-robin routing
    """
    return Router(strategy="round-robin")


@pytest.fixture
def router_random() -> Router:
    """Create a Router with random strategy.
    
    Returns:
        Router instance configured for random provider selection
    """
    return Router(strategy="random")


@pytest.fixture
def router_first_available() -> Router:
    """Create a Router with first-available strategy.
    
    Returns:
        Router instance configured to select first healthy provider
    """
    return Router(strategy="first-available")


@pytest.fixture
def router_with_providers(router_round_robin: Router) -> Router:
    """Create a Router with 3 normal providers.
    
    This fixture adds 3 MockProvider instances in normal mode to the router.
    Useful for testing routing strategies and fallback mechanisms.
    
    Args:
        router_round_robin: Router fixture with round-robin strategy
    
    Returns:
        Router instance with 3 providers already registered
    """
    for i in range(3):
        config = ProviderConfig(name=f"provider-{i+1}", model="mock-normal")
        router_round_robin.add_provider(MockProvider(config))
    return router_round_robin


# ============================================================================
# Retrieval module fixtures (for integration tests)
# ============================================================================

try:
    from langchain_community.embeddings import FakeEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


@pytest.fixture(scope="session")
def synthetic_faiss_index():
    """Large synthetic FAISS index (1000 docs, 384-dim) for integration tests.

    This fixture creates a FAISS index with 1000 synthetic documents using
    FakeEmbeddings, which is fast (~50-100ms) and reproducible.

    The fixture uses session scope, meaning it's created once for all
    integration tests, significantly speeding up test execution.

    Document structure:
    - page_content: "Synthetic document {i} about topic {i % 10}. Additional..."
    - metadata: {"id": i, "topic": i % 10, "group": i // 100}

    This structure allows testing:
    - Similarity search with various k values
    - Metadata filtering (by id, topic, group)
    - MMR search for diversity
    - Concurrent queries on a realistic index size

    Returns:
        FAISS vectorstore with 1000 documents (384-dim embeddings)

    Raises:
        pytest.skip: If langchain-community not installed

    Example:
        >>> async def test_integration(synthetic_faiss_index):
        ...     retriever = AsyncFAISSRetriever(synthetic_faiss_index)
        ...     docs = await retriever.similarity_search("topic 5", k=10)
        ...     assert len(docs) == 10
    """
    if not LANGCHAIN_AVAILABLE:
        pytest.skip(
            "langchain-community not installed. "
            "Install with: pip install multi-llm-orchestrator[retrieval]"
        )

    # Use FakeEmbeddings for fast, reproducible embeddings
    embeddings = FakeEmbeddings(size=384)

    # Create 1000 synthetic documents
    docs = [
        Document(
            page_content=(
                f"Synthetic document {i} about topic {i % 10}. "
                f"This document contains additional content to make it realistic. "
                f"It belongs to group {i // 100} and has unique identifier {i}."
            ),
            metadata={"id": i, "topic": i % 10, "group": i // 100},
        )
        for i in range(1000)
    ]

    # Create FAISS index (~50-100ms for 1000 docs)
    return FAISS.from_documents(docs, embeddings)
