"""Unit tests for BaseAsyncRetriever ABC."""

import pytest

from orchestrator.retrieval.base import BaseAsyncRetriever


class ConcreteRetriever(BaseAsyncRetriever):
    """Concrete implementation of BaseAsyncRetriever for testing."""

    async def similarity_search(
        self, query: str, k: int = 4, filter=None, **kwargs
    ):
        """Minimal implementation for testing."""
        return []  # type: ignore[return-value]

    async def similarity_search_with_score(
        self, query: str, k: int = 4, filter=None, **kwargs
    ):
        """Minimal implementation for testing."""
        return []  # type: ignore[return-value]


class TestBaseAsyncRetriever:
    """Test BaseAsyncRetriever abstract base class."""

    async def test_mmr_not_implemented_by_default(self):
        """Test MMR raises NotImplementedError if not overridden."""
        retriever = ConcreteRetriever()

        with pytest.raises(
            NotImplementedError, match="does not support MMR search"
        ):
            await retriever.max_marginal_relevance_search("query", k=5)

    async def test_mmr_error_message_includes_class_name(self):
        """Test MMR NotImplementedError includes class name."""
        retriever = ConcreteRetriever()

        with pytest.raises(
            NotImplementedError, match="ConcreteRetriever"
        ):
            await retriever.max_marginal_relevance_search("query")

    async def test_abstract_methods_must_be_implemented(self):
        """Test that subclasses must implement abstract methods."""
        # This test ensures ABC enforcement works

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # Try to instantiate without implementing abstract methods
            class IncompleteRetriever(BaseAsyncRetriever):  # type: ignore[misc]
                pass

            IncompleteRetriever()  # Should raise TypeError
