"""Exceptions for retrieval operations.

This module provides a hierarchy of exceptions for handling errors
in async vector store retrieval operations.

Example:
    >>> from orchestrator.retrieval.errors import InvalidQueryError
    >>> raise InvalidQueryError("k must be >= 1")
"""


class RetrieverError(Exception):
    """Base exception for all retrieval operations.

    All retrieval-specific exceptions inherit from this base class,
    allowing for unified error handling across different retriever
    implementations.

    Example:
        >>> try:
        ...     docs = await retriever.similarity_search("query")
        ... except RetrieverError as e:
        ...     logger.error(f"Retrieval error: {e}")
    """

    pass


class VectorStoreError(RetrieverError):
    """Vector store operation failed.

    Raised when:
    - FAISS index is corrupted
    - Embedding dimension mismatch
    - Index not initialized properly
    - Vector store internal error

    Example:
        >>> if index.d != expected_dim:
        ...     raise VectorStoreError(f"Dimension mismatch: {index.d} != {expected_dim}")
    """

    pass


class InvalidQueryError(RetrieverError):
    """Invalid search query parameters.

    Raised when:
    - k < 1 (invalid number of results)
    - fetch_k < k (invalid fetch size)
    - Invalid filter syntax
    - Empty query string
    - Invalid parameter types

    Example:
        >>> if k < 1:
        ...     raise InvalidQueryError("k must be >= 1")
    """

    pass


class ThreadPoolError(RetrieverError):
    """Thread pool execution failed.

    Raised when:
    - Thread pool is shutdown
    - Executor rejected task
    - Thread execution timeout
    - Unexpected thread pool error

    Example:
        >>> try:
        ...     result = await asyncio.to_thread(func)
        ... except RuntimeError as e:
        ...     raise ThreadPoolError(f"Thread pool execution failed: {e}")
    """

    pass


class DependencyError(RetrieverError):
    """Required dependency not installed.

    Raised when:
    - faiss-cpu is not installed
    - langchain-community is not installed
    - Incompatible dependency versions

    This exception provides user-friendly installation instructions
    to help users resolve the missing dependency issue.

    Example:
        >>> retriever = AsyncFAISSRetriever(vectorstore)
        DependencyError: AsyncFAISSRetriever requires 'faiss-cpu>=1.7.4' and
        'langchain-community>=0.0.38'.
        Install with: pip install multi-llm-orchestrator[retrieval]
    """

    def __init__(self, message: str = "") -> None:
        """Initialize DependencyError with user-friendly message.

        Args:
            message: Custom error message. If empty, uses default message
                    with installation instructions.
        """
        if not message:
            message = (
                "AsyncFAISSRetriever requires 'faiss-cpu>=1.7.4' and "
                "'langchain-community>=0.0.38'. "
                "Install with: pip install multi-llm-orchestrator[retrieval]"
            )
        super().__init__(message)
