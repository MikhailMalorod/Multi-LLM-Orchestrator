"""Base retriever interface for async vector store implementations.

This module provides the abstract base class that all async retrievers
must implement, ensuring a consistent interface across different
vector store backends (FAISS, Qdrant, Pinecone, etc.).

Example:
    >>> from orchestrator.retrieval import BaseAsyncRetriever
    >>> class MyRetriever(BaseAsyncRetriever):
    ...     async def similarity_search(self, query, k=4, **kwargs):
    ...         # Implementation here
    ...         pass
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.documents import Document
else:
    try:
        from langchain_core.documents import Document

        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        Document = Any  # type: ignore[misc]


class BaseAsyncRetriever(ABC):
    """Abstract base class for async vector store retrievers.

    This class defines the unified interface that all retriever implementations
    must follow. It provides abstract methods for similarity search operations
    and an optional method for Maximum Marginal Relevance (MMR) search.

    Implementations should use asyncio.to_thread() or native async APIs
    to prevent GIL blocking in shared event loops.

    Attributes:
        Subclasses define their own attributes (e.g., vectorstore, executor)

    Example:
        >>> class MyAsyncRetriever(BaseAsyncRetriever):
        ...     async def similarity_search(self, query, k=4, **kwargs):
        ...         return await asyncio.to_thread(
        ...             self.vectorstore.similarity_search, query, k
        ...         )
        ...
        ...     async def similarity_search_with_score(self, query, k=4, **kwargs):
        ...         return await asyncio.to_thread(
        ...             self.vectorstore.similarity_search_with_score, query, k
        ...         )
    """

    @abstractmethod
    async def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Callable[[dict[str, Any]], bool] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Perform async similarity search.

        Args:
            query: Query text to search for
            k: Number of documents to return (default: 4)
            filter: Optional filter for metadata (dict or callable)
            **kwargs: Additional provider-specific parameters

        Returns:
            List of relevant documents sorted by similarity

        Raises:
            InvalidQueryError: If query parameters are invalid
            VectorStoreError: If vector store operation fails
            ThreadPoolError: If async execution fails

        Example:
            >>> retriever = MyAsyncRetriever(vectorstore)
            >>> docs = await retriever.similarity_search("python tutorial", k=5)
            >>> print(len(docs))
            5
        """
        pass

    @abstractmethod
    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Callable[[dict[str, Any]], bool] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[tuple[Document, float]]:
        """Perform async similarity search with relevance scores.

        Args:
            query: Query text to search for
            k: Number of documents to return (default: 4)
            filter: Optional filter for metadata (dict or callable)
            **kwargs: Additional provider-specific parameters

        Returns:
            List of (document, score) tuples sorted by similarity.
            Score interpretation depends on the vector store implementation
            (e.g., L2 distance for FAISS, where lower is better).

        Raises:
            InvalidQueryError: If query parameters are invalid
            VectorStoreError: If vector store operation fails
            ThreadPoolError: If async execution fails

        Example:
            >>> retriever = MyAsyncRetriever(vectorstore)
            >>> results = await retriever.similarity_search_with_score("python", k=3)
            >>> for doc, score in results:
            ...     print(f"Score: {score:.4f}, Content: {doc.page_content[:50]}")
        """
        pass

    async def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Callable[[dict[str, Any]], bool] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Perform Maximum Marginal Relevance (MMR) search for diversity.

        MMR balances relevance and diversity by selecting documents that are
        relevant to the query while being diverse from already selected documents.

        This is an optional method with a default implementation that raises
        NotImplementedError. Subclasses should override this if their vector
        store supports MMR search.

        Args:
            query: Query text to search for
            k: Number of documents to return (default: 4)
            fetch_k: Number of documents to fetch before MMR (default: 20)
            lambda_mult: Diversity parameter (0=max diversity, 1=min diversity)
            filter: Optional filter for metadata (dict or callable)
            **kwargs: Additional provider-specific parameters

        Returns:
            List of diverse relevant documents

        Raises:
            NotImplementedError: If MMR is not supported by the implementation
            InvalidQueryError: If query parameters are invalid
            VectorStoreError: If vector store operation fails
            ThreadPoolError: If async execution fails

        Example:
            >>> retriever = MyAsyncRetriever(vectorstore)
            >>> docs = await retriever.max_marginal_relevance_search(
            ...     "machine learning", k=5, lambda_mult=0.7
            ... )
            >>> # Returns 5 documents that are relevant but diverse
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support MMR search. "
            "Override max_marginal_relevance_search() to implement."
        )
