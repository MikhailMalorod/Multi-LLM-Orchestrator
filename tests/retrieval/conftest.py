"""Fixtures for retrieval module tests."""

from unittest.mock import MagicMock

import pytest

try:
    from langchain_community.embeddings import FakeEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    pytest.skip(
        "langchain-community not installed. "
        "Install with: pip install multi-llm-orchestrator[retrieval]",
        allow_module_level=True,
    )


@pytest.fixture
def mock_faiss_vectorstore() -> MagicMock:
    """Mock FAISS vectorstore for pure unit tests (without real index).

    Returns a MagicMock with pre-configured return values for:
    - similarity_search: Returns 2 mock documents
    - similarity_search_with_score: Returns 2 (doc, score) tuples
    - max_marginal_relevance_search: Returns 1 mock document
    - index.ntotal: 100 (mock index size)
    - index.d: 384 (mock vector dimension)

    This fixture is useful for testing AsyncFAISSRetriever logic without
    the overhead of creating a real FAISS index.

    Example:
        >>> def test_something(mock_faiss_vectorstore):
        ...     retriever = AsyncFAISSRetriever(mock_faiss_vectorstore)
        ...     # Test retriever logic
    """
    mock = MagicMock(spec=FAISS)

    # Configure similarity_search
    mock.similarity_search.return_value = [
        Document(page_content="Mock document 1", metadata={"id": 1, "topic": "python"}),
        Document(page_content="Mock document 2", metadata={"id": 2, "topic": "async"}),
    ]

    # Configure similarity_search_with_score
    mock.similarity_search_with_score.return_value = [
        (
            Document(
                page_content="Mock document 1", metadata={"id": 1, "topic": "python"}
            ),
            0.95,
        ),
        (
            Document(
                page_content="Mock document 2", metadata={"id": 2, "topic": "async"}
            ),
            0.85,
        ),
    ]

    # Configure max_marginal_relevance_search
    mock.max_marginal_relevance_search.return_value = [
        Document(page_content="Mock document 1", metadata={"id": 1, "topic": "python"}),
    ]

    # Mock index attributes (ntotal, d)
    mock_index = MagicMock()
    mock_index.ntotal = 100
    mock_index.d = 384
    mock.index = mock_index

    return mock


@pytest.fixture
def small_faiss_index() -> FAISS:
    """Small synthetic FAISS index (100 docs, 384-dim) for unit tests.

    Creates a FAISS index with 100 synthetic documents using FakeEmbeddings,
    which is fast (~10-20ms) and reproducible.

    Documents are structured with:
    - page_content: "Test document {i} with content about topic {i % 5}"
    - metadata: {"id": i, "topic": i % 5}

    This allows testing:
    - Similarity search with different k values
    - Metadata filtering (by id or topic)
    - MMR search
    - Concurrent queries

    Returns:
        FAISS vectorstore with 100 documents (384-dim embeddings)

    Example:
        >>> async def test_search(small_faiss_index):
        ...     retriever = AsyncFAISSRetriever(small_faiss_index)
        ...     docs = await retriever.similarity_search("topic 1", k=5)
        ...     assert len(docs) == 5
    """
    # Use FakeEmbeddings for fast, reproducible embeddings
    embeddings = FakeEmbeddings(size=384)

    # Create 100 synthetic documents
    docs = [
        Document(
            page_content=f"Test document {i} with content about topic {i % 5}",
            metadata={"id": i, "topic": i % 5},
        )
        for i in range(100)
    ]

    # Create FAISS index (~10-20ms)
    return FAISS.from_documents(docs, embeddings)


@pytest.fixture
def tiny_faiss_index() -> FAISS:
    """Tiny FAISS index (10 docs, 384-dim) for fast tests.

    Even faster than small_faiss_index (~2-5ms), useful for tests
    that don't need many documents (e.g., validation tests).

    Returns:
        FAISS vectorstore with 10 documents (384-dim embeddings)

    Example:
        >>> async def test_validation(tiny_faiss_index):
        ...     retriever = AsyncFAISSRetriever(tiny_faiss_index)
        ...     with pytest.raises(InvalidQueryError):
        ...         await retriever.similarity_search("", k=5)
    """
    embeddings = FakeEmbeddings(size=384)

    docs = [
        Document(
            page_content=f"Tiny document {i}",
            metadata={"id": i},
        )
        for i in range(10)
    ]

    return FAISS.from_documents(docs, embeddings)
