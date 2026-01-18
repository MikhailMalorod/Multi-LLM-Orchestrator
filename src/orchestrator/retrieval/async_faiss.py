"""AsyncFAISSRetriever implementation.

Provides async wrapper for LangChain FAISS vectorstore with GIL
mitigation through asyncio.to_thread() for CPU-bound operations.

This module enables concurrent retrieval in shared asyncio event loops
(e.g., Telegram bot pools, FastAPI applications) without blocking
the event loop during FAISS index search operations.

Example:
    >>> from orchestrator.retrieval import AsyncFAISSRetriever
    >>> from langchain_community.vectorstores import FAISS
    >>>
    >>> # Create FAISS vectorstore
    >>> vectorstore = FAISS.from_documents(docs, embeddings)
    >>>
    >>> # Wrap in AsyncFAISSRetriever
    >>> retriever = AsyncFAISSRetriever(vectorstore)
    >>>
    >>> # Async search (GIL-free!)
    >>> docs = await retriever.similarity_search("query", k=5)
"""

import asyncio
import logging
import warnings
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, cast

from .base import BaseAsyncRetriever
from .errors import DependencyError, InvalidQueryError, ThreadPoolError

# Try to import FAISS (optional dependency)
try:
    from langchain_community.vectorstores.faiss import FAISS
    from langchain_core.documents import Document

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Type-checking only imports (avoid runtime ImportError)
if TYPE_CHECKING:
    from langchain_core.documents import Document
else:
    if not FAISS_AVAILABLE:
        FAISS = None  # type: ignore[assignment]
        Document = Any

# Logger for debugging and observability
logger = logging.getLogger(__name__)


class AsyncFAISSRetriever(BaseAsyncRetriever):
    """Async FAISS retriever with GIL mitigation.

    This class provides async wrappers for LangChain FAISS vectorstore
    operations, using asyncio.to_thread() to offload CPU-bound FAISS
    operations to a thread pool. This prevents GIL blocking in shared
    asyncio event loops.

    Thread Safety:
        FAISS index is thread-safe for read operations. Multiple concurrent
        queries can safely execute in parallel without locks.

    Attributes:
        vectorstore: LangChain FAISS vectorstore instance
        _executor: Optional custom ThreadPoolExecutor
        _owns_executor: Whether this instance owns the executor
        _max_workers: Max threads if executor owned

    Example:
        >>> # Basic usage
        >>> retriever = AsyncFAISSRetriever(faiss_index)
        >>> docs = await retriever.similarity_search("python tutorial", k=5)
        >>>
        >>> # With custom executor
        >>> executor = ThreadPoolExecutor(max_workers=10)
        >>> retriever = AsyncFAISSRetriever(faiss_index, executor=executor)
        >>>
        >>> # With context manager
        >>> async with AsyncFAISSRetriever(faiss_index, max_workers=10) as retriever:
        ...     docs = await retriever.similarity_search("query")
    """

    vectorstore: Any  # FAISS if available
    _executor: ThreadPoolExecutor | None
    _owns_executor: bool
    _max_workers: int | None

    def __init__(
        self,
        vectorstore: Any,
        executor: ThreadPoolExecutor | None = None,
        max_workers: int | None = None,
    ) -> None:
        """Initialize AsyncFAISSRetriever.

        Args:
            vectorstore: LangChain FAISS vectorstore instance
            executor: Optional custom ThreadPoolExecutor. If None, uses
                     asyncio default thread pool.
            max_workers: Max threads if creating internal executor. Ignored
                        if executor is provided. If None, uses asyncio default.

        Raises:
            DependencyError: If faiss-cpu or langchain-community not installed
            TypeError: If vectorstore is not a FAISS instance

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index)
            >>> retriever = AsyncFAISSRetriever(faiss_index, max_workers=10)
            >>> retriever = AsyncFAISSRetriever(faiss_index, executor=custom_executor)
        """
        # Check dependencies
        if not FAISS_AVAILABLE:
            raise DependencyError()

        # Validate vectorstore type
        if not isinstance(vectorstore, FAISS):
            raise TypeError(
                f"vectorstore must be FAISS instance, got {type(vectorstore).__name__}"
            )

        self.vectorstore = vectorstore
        self._executor = executor
        self._max_workers = max_workers

        # Determine ownership
        if executor is None and max_workers is not None:
            # Create owned executor
            self._owns_executor = True
            self._executor = ThreadPoolExecutor(max_workers=max_workers)
            logger.debug(
                f"Created internal ThreadPoolExecutor with max_workers={max_workers}"
            )
        else:
            self._owns_executor = False

        logger.info(
            f"Initialized AsyncFAISSRetriever(index_size={vectorstore.index.ntotal}, "
            f"dimension={vectorstore.index.d}, "
            f"executor={'custom' if executor else 'asyncio_default'})"
        )

    async def close(self) -> None:
        """Close internal executor if owned.

        This method should be called when the retriever is no longer needed,
        especially if using a custom executor or max_workers parameter.

        This method is idempotent - can be called multiple times safely.

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index, max_workers=10)
            >>> try:
            ...     docs = await retriever.similarity_search("query")
            ... finally:
            ...     await retriever.close()
        """
        if self._owns_executor and self._executor is not None:
            logger.debug("Shutting down owned ThreadPoolExecutor")
            self._executor.shutdown(wait=True)
            self._executor = None

    async def __aenter__(self) -> "AsyncFAISSRetriever":
        """Enter async context manager.

        Returns:
            Self for use in async with statement

        Example:
            >>> async with AsyncFAISSRetriever(faiss_index, max_workers=10) as retriever:
            ...     docs = await retriever.similarity_search("query")
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager.

        Automatically calls close() to cleanup executor.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        await self.close()

    def __del__(self) -> None:
        """Cleanup executor on garbage collection.

        If the executor was not properly closed, emits a ResourceWarning
        and attempts to shutdown the executor (may fail if event loop closed).
        """
        if self._owns_executor and self._executor is not None:
            warnings.warn(
                "AsyncFAISSRetriever was not properly closed. "
                "Use 'async with AsyncFAISSRetriever(...)' or call 'await retriever.close()'.",
                ResourceWarning,
                stacklevel=2,
            )
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                # Ignore errors during cleanup (event loop may be closed)
                pass

    async def _run_in_thread(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Internal helper to offload sync operations to thread pool.

        Args:
            func: Sync function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            ThreadPoolError: If thread pool execution fails
        """
        try:
            if self._executor is not None:
                # Use custom executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    self._executor, lambda: func(*args, **kwargs)
                )
            else:
                # Use asyncio default thread pool
                return await asyncio.to_thread(func, *args, **kwargs)
        except (RuntimeError, ValueError, TypeError) as e:
            # Catch expected exceptions (NOT KeyboardInterrupt, SystemExit)
            raise ThreadPoolError(f"Thread pool execution failed: {e}") from e

    async def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Callable[[dict[str, Any]], bool] | dict[str, Any] | None = None,
        fetch_k: int = 20,
        **kwargs: Any,
    ) -> list[Document]:
        """Async similarity search with GIL mitigation.

        Offloads CPU-bound FAISS similarity_search() to thread pool,
        preventing GIL blocking in shared asyncio event loops.

        Args:
            query: Query text to search for
            k: Number of documents to return (default: 4)
            filter: Optional filter (dict or callable)
                   - Dict: {"key": "value"} or {"key": {"$eq": "value"}}
                   - Callable: lambda metadata: bool
            fetch_k: Number of documents to fetch before filtering (default: 20)
            **kwargs: Additional arguments for FAISS (e.g., score_threshold)

        Returns:
            List of relevant documents sorted by similarity

        Raises:
            InvalidQueryError: If parameters are invalid
            ThreadPoolError: If thread pool execution fails

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index)
            >>> docs = await retriever.similarity_search("python tutorial", k=5)
            >>> print(len(docs))
            5
            >>>
            >>> # With filter
            >>> docs = await retriever.similarity_search(
            ...     "query", k=5, filter={"page": 1}
            ... )
        """
        # Type validation
        if not isinstance(query, str):
            raise InvalidQueryError(
                f"query must be str, got {type(query).__name__}"
            )
        if not isinstance(k, int):
            raise InvalidQueryError(f"k must be int, got {type(k).__name__}")
        if not isinstance(fetch_k, int):
            raise InvalidQueryError(
                f"fetch_k must be int, got {type(fetch_k).__name__}"
            )

        # Value validation
        if k < 1:
            raise InvalidQueryError(f"k must be >= 1, got {k}")
        if fetch_k < k:
            raise InvalidQueryError(
                f"fetch_k ({fetch_k}) must be >= k ({k})"
            )
        if not query.strip():
            raise InvalidQueryError("query cannot be empty")

        logger.debug(
            f"similarity_search(query_len={len(query)}, k={k}, "
            f"filter={filter is not None}, fetch_k={fetch_k})"
        )

        # Offload to thread pool
        try:
            results = await self._run_in_thread(
                self.vectorstore.similarity_search,
                query,
                k=k,
                filter=filter,
                fetch_k=fetch_k,
                **kwargs,
            )
            return cast("list[Document]", results)
        except ThreadPoolError:
            raise
        except Exception as e:
            raise ThreadPoolError(
                f"FAISS similarity_search failed: {e}"
            ) from e

    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 4,
        filter: Callable[[dict[str, Any]], bool] | dict[str, Any] | None = None,
        fetch_k: int = 20,
        **kwargs: Any,
    ) -> list[tuple[Document, float]]:
        """Async similarity search with scores (L2 distance).

        Returns documents with their similarity scores. Lower scores
        indicate higher similarity (L2 distance).

        Args:
            query: Query text to search for
            k: Number of documents to return (default: 4)
            filter: Optional filter (dict or callable)
            fetch_k: Number of documents to fetch before filtering (default: 20)
            **kwargs: Additional arguments for FAISS

        Returns:
            List of (document, score) tuples sorted by similarity.
            Lower score = more similar (L2 distance).

        Raises:
            InvalidQueryError: If parameters are invalid
            ThreadPoolError: If thread pool execution fails

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index)
            >>> results = await retriever.similarity_search_with_score("query", k=3)
            >>> for doc, score in results:
            ...     print(f"Score: {score:.4f}, Content: {doc.page_content[:50]}")
        """
        # Type validation
        if not isinstance(query, str):
            raise InvalidQueryError(
                f"query must be str, got {type(query).__name__}"
            )
        if not isinstance(k, int):
            raise InvalidQueryError(f"k must be int, got {type(k).__name__}")
        if not isinstance(fetch_k, int):
            raise InvalidQueryError(
                f"fetch_k must be int, got {type(fetch_k).__name__}"
            )

        # Value validation
        if k < 1:
            raise InvalidQueryError(f"k must be >= 1, got {k}")
        if fetch_k < k:
            raise InvalidQueryError(
                f"fetch_k ({fetch_k}) must be >= k ({k})"
            )
        if not query.strip():
            raise InvalidQueryError("query cannot be empty")

        logger.debug(
            f"similarity_search_with_score(query_len={len(query)}, k={k}, "
            f"filter={filter is not None}, fetch_k={fetch_k})"
        )

        # Offload to thread pool
        try:
            results = await self._run_in_thread(
                self.vectorstore.similarity_search_with_score,
                query,
                k=k,
                filter=filter,
                fetch_k=fetch_k,
                **kwargs,
            )
            return cast("list[tuple[Document, float]]", results)
        except ThreadPoolError:
            raise
        except Exception as e:
            raise ThreadPoolError(
                f"FAISS similarity_search_with_score failed: {e}"
            ) from e

    async def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        filter: Callable[[dict[str, Any]], bool] | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Async MMR search (diversity-aware retrieval).

        Maximum Marginal Relevance balances relevance and diversity by
        selecting documents that are relevant to the query while being
        diverse from already selected documents.

        Args:
            query: Query text to search for
            k: Number of documents to return (default: 4)
            fetch_k: Number of documents to fetch before MMR (default: 20)
            lambda_mult: Diversity parameter (0=max diversity, 1=min diversity)
            filter: Optional filter (dict or callable)
            **kwargs: Additional arguments for FAISS

        Returns:
            List of diverse relevant documents

        Raises:
            InvalidQueryError: If parameters are invalid
            ThreadPoolError: If thread pool execution fails

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index)
            >>> docs = await retriever.max_marginal_relevance_search(
            ...     "machine learning", k=5, lambda_mult=0.7
            ... )
            >>> # Returns 5 documents that are relevant but diverse
        """
        # Type validation
        if not isinstance(query, str):
            raise InvalidQueryError(
                f"query must be str, got {type(query).__name__}"
            )
        if not isinstance(k, int):
            raise InvalidQueryError(f"k must be int, got {type(k).__name__}")
        if not isinstance(fetch_k, int):
            raise InvalidQueryError(
                f"fetch_k must be int, got {type(fetch_k).__name__}"
            )
        if not isinstance(lambda_mult, (int, float)):
            raise InvalidQueryError(
                f"lambda_mult must be float, got {type(lambda_mult).__name__}"
            )

        # Value validation
        if k < 1:
            raise InvalidQueryError(f"k must be >= 1, got {k}")
        if fetch_k < k:
            raise InvalidQueryError(
                f"fetch_k ({fetch_k}) must be >= k ({k})"
            )
        if not 0 <= lambda_mult <= 1:
            raise InvalidQueryError(
                f"lambda_mult must be in [0, 1], got {lambda_mult}"
            )
        if not query.strip():
            raise InvalidQueryError("query cannot be empty")

        logger.debug(
            f"max_marginal_relevance_search(query_len={len(query)}, k={k}, "
            f"fetch_k={fetch_k}, lambda_mult={lambda_mult}, "
            f"filter={filter is not None})"
        )

        # Offload to thread pool
        try:
            results = await self._run_in_thread(
                self.vectorstore.max_marginal_relevance_search,
                query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
                filter=filter,
                **kwargs,
            )
            return cast("list[Document]", results)
        except ThreadPoolError:
            raise
        except Exception as e:
            raise ThreadPoolError(
                f"FAISS max_marginal_relevance_search failed: {e}"
            ) from e

    def get_vectorstore_info(self) -> dict[str, Any]:
        """Get vectorstore metadata for debugging.

        Returns:
            Dict with vectorstore metadata:
                - vectorstore_type: "FAISS"
                - index_size: Number of vectors in index
                - dimension: Vector dimension
                - executor_type: Executor type ("custom", "asyncio_default", or "owned")

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index)
            >>> info = retriever.get_vectorstore_info()
            >>> print(info)
            {'vectorstore_type': 'FAISS', 'index_size': 1000, 'dimension': 384, ...}
        """
        executor_type = (
            "custom"
            if self._executor and not self._owns_executor
            else "owned" if self._owns_executor else "asyncio_default"
        )

        return {
            "vectorstore_type": "FAISS",
            "index_size": self.vectorstore.index.ntotal,
            "dimension": self.vectorstore.index.d,
            "executor_type": executor_type,
            "max_workers": self._max_workers,
        }

    def __repr__(self) -> str:
        """User-friendly repr for debugging.

        Returns:
            String representation with key metadata

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index)
            >>> print(repr(retriever))
            AsyncFAISSRetriever(index_size=1000, dimension=384, executor=default)
        """
        executor_str = (
            "custom"
            if self._executor and not self._owns_executor
            else f"owned({self._max_workers})" if self._owns_executor else "default"
        )

        return (
            f"AsyncFAISSRetriever("
            f"index_size={self.vectorstore.index.ntotal}, "
            f"dimension={self.vectorstore.index.d}, "
            f"executor={executor_str})"
        )

    def as_retriever(
        self,
        search_type: str = "similarity",
        search_kwargs: dict[str, Any] | None = None,
    ) -> Any:  # AsyncFAISSVectorStoreRetriever
        """Create LangChain BaseRetriever wrapper.

        Factory method to create a LangChain-compatible retriever that
        can be used in LangChain chains.

        Args:
            search_type: Type of search ("similarity" or "mmr")
            search_kwargs: Additional search parameters (e.g., {"k": 5})

        Returns:
            AsyncFAISSVectorStoreRetriever instance (LangChain BaseRetriever)

        Raises:
            DependencyError: If langchain-core not installed
            ValueError: If search_type is invalid

        Example:
            >>> retriever = AsyncFAISSRetriever(faiss_index)
            >>> lc_retriever = retriever.as_retriever(
            ...     search_type="similarity",
            ...     search_kwargs={"k": 5}
            ... )
            >>> docs = await lc_retriever.ainvoke("query")
        """
        # Lazy import to avoid circular dependency
        from .langchain_compat import AsyncFAISSVectorStoreRetriever  # noqa: I001

        return AsyncFAISSVectorStoreRetriever(
            async_retriever=self,
            search_type=search_type,
            search_kwargs=search_kwargs or {},
        )
