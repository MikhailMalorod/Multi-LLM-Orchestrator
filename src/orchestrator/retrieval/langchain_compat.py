"""LangChain BaseRetriever compatibility wrapper.

This module provides AsyncFAISSVectorStoreRetriever, a LangChain-compatible
retriever that wraps AsyncFAISSRetriever for use in LangChain chains.

Example:
    >>> from orchestrator.retrieval import AsyncFAISSRetriever
    >>> from langchain_community.vectorstores import FAISS
    >>>
    >>> # Create FAISS vectorstore
    >>> vectorstore = FAISS.from_documents(docs, embeddings)
    >>>
    >>> # Wrap in AsyncFAISSRetriever
    >>> async_retriever = AsyncFAISSRetriever(vectorstore)
    >>>
    >>> # Create LangChain-compatible retriever
    >>> lc_retriever = async_retriever.as_retriever(
    ...     search_type="similarity",
    ...     search_kwargs={"k": 5}
    ... )
    >>>
    >>> # Use in LangChain chains
    >>> docs = await lc_retriever.ainvoke("query")
"""

import warnings
from typing import TYPE_CHECKING, Any, cast

try:
    from pydantic import Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    Field = None  # type: ignore[assignment]

from .errors import DependencyError

# Try to import LangChain dependencies
try:
    from langchain_core.callbacks import (
        AsyncCallbackManagerForRetrieverRun,
        CallbackManagerForRetrieverRun,
    )
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Type-checking imports
if TYPE_CHECKING:
    from langchain_core.callbacks import (
        AsyncCallbackManagerForRetrieverRun,
        CallbackManagerForRetrieverRun,
    )
    from langchain_core.documents import Document
    from langchain_core.retrievers import BaseRetriever

    from .async_faiss import AsyncFAISSRetriever
else:
    if not LANGCHAIN_AVAILABLE:
        BaseRetriever = object  # type: ignore[misc]
        Document = Any  # type: ignore[misc]
        CallbackManagerForRetrieverRun = Any  # type: ignore[misc]
        AsyncCallbackManagerForRetrieverRun = Any  # type: ignore[misc]


class AsyncFAISSVectorStoreRetriever(BaseRetriever):
    """LangChain BaseRetriever wrapper for AsyncFAISSRetriever.

    This class provides a standard LangChain retriever interface (invoke/ainvoke)
    while using AsyncFAISSRetriever internally for GIL-free retrieval operations.

    The wrapper supports both synchronous and asynchronous retrieval:
    - ainvoke() / _aget_relevant_documents(): Async, GIL-free (RECOMMENDED)
    - invoke() / _get_relevant_documents(): Sync, blocks GIL (DEPRECATED)

    Attributes:
        async_retriever: Underlying AsyncFAISSRetriever instance
        search_type: Type of search ("similarity" or "mmr")
        search_kwargs: Search parameters (k, fetch_k, lambda_mult, filter, etc.)

    Example:
        >>> # Create via as_retriever() factory method
        >>> async_retriever = AsyncFAISSRetriever(faiss_index)
        >>> lc_retriever = async_retriever.as_retriever(
        ...     search_type="similarity",
        ...     search_kwargs={"k": 5, "filter": {"page": 1}}
        ... )
        >>>
        >>> # Use in async context (RECOMMENDED)
        >>> docs = await lc_retriever.ainvoke("python tutorial")
        >>> print(len(docs))
        5
        >>>
        >>> # Use in LangChain chains
        >>> from langchain_core.runnables import RunnablePassthrough
        >>> chain = {"context": lc_retriever, "question": RunnablePassthrough()}
        >>> result = await chain.ainvoke("What is Python?")
    """

    async_retriever: Any  # AsyncFAISSRetriever (avoid circular import)
    search_type: str = "similarity"
    search_kwargs: dict[str, Any] = Field(default_factory=dict)

    def __init__(
        self,
        async_retriever: "AsyncFAISSRetriever",
        search_type: str = "similarity",
        search_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize LangChain retriever wrapper.

        Args:
            async_retriever: AsyncFAISSRetriever instance to wrap
            search_type: Type of search to perform ("similarity" or "mmr")
            search_kwargs: Search parameters to pass to retriever methods:
                          - k: Number of documents (default: 4)
                          - fetch_k: Fetch before filtering (default: 20)
                          - lambda_mult: MMR diversity (default: 0.5)
                          - filter: Metadata filter (dict or callable)
            **kwargs: Additional BaseRetriever arguments

        Raises:
            DependencyError: If langchain-core not installed
            ValueError: If search_type is not "similarity" or "mmr"
            TypeError: If async_retriever is not AsyncFAISSRetriever

        Example:
            >>> from orchestrator.retrieval import AsyncFAISSRetriever
            >>> async_retriever = AsyncFAISSRetriever(faiss_index)
            >>>
            >>> # Similarity search
            >>> lc_retriever = AsyncFAISSVectorStoreRetriever(
            ...     async_retriever=async_retriever,
            ...     search_type="similarity",
            ...     search_kwargs={"k": 5}
            ... )
            >>>
            >>> # MMR search
            >>> lc_retriever_mmr = AsyncFAISSVectorStoreRetriever(
            ...     async_retriever=async_retriever,
            ...     search_type="mmr",
            ...     search_kwargs={"k": 5, "lambda_mult": 0.7}
            ... )
        """
        # Check dependencies
        if not LANGCHAIN_AVAILABLE:
            raise DependencyError(
                "AsyncFAISSVectorStoreRetriever requires 'langchain-core>=0.1.0'. "
                "Install with: pip install multi-llm-orchestrator[retrieval]"
            )

        # Validate search_type
        if search_type not in {"similarity", "mmr"}:
            raise ValueError(
                f"search_type must be 'similarity' or 'mmr', got '{search_type}'"
            )

        # Validate async_retriever type (avoid circular import with string check)
        if not hasattr(async_retriever, "similarity_search"):
            raise TypeError(
                "async_retriever must be AsyncFAISSRetriever instance, "
                f"got {type(async_retriever).__name__}"
            )

        # Normalize search_kwargs
        normalized_search_kwargs = search_kwargs or {}

        # Initialize Pydantic model with all fields
        # BaseRetriever doesn't use these, but Pydantic needs them for validation
        super().__init__(
            async_retriever=async_retriever,  # type: ignore[call-arg]
            search_type=search_type,
            search_kwargs=normalized_search_kwargs,
        )

    # Pydantic v2 config for arbitrary types (AsyncFAISSRetriever)
    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: "CallbackManagerForRetrieverRun | None" = None,
    ) -> list["Document"]:
        """Synchronous retrieval (DEPRECATED - blocks GIL!).

        ⚠️ WARNING: This method performs synchronous FAISS search, which
        blocks the GIL and defeats the purpose of AsyncFAISSRetriever.

        Use ainvoke() or _aget_relevant_documents() instead for async,
        GIL-free retrieval.

        This method exists only for backward compatibility with synchronous
        LangChain code. If you call it in an async context, the entire
        event loop will block during FAISS search.

        Args:
            query: Query text to search for
            run_manager: Optional callback manager (unused)

        Returns:
            List of relevant documents

        Raises:
            ValueError: If search_type is invalid
            RuntimeError: If retrieval fails

        Example:
            >>> lc_retriever = async_retriever.as_retriever()
            >>> # ❌ BAD: Blocks GIL
            >>> docs = lc_retriever.invoke("query")
            >>>
            >>> # ✅ GOOD: Async, GIL-free
            >>> docs = await lc_retriever.ainvoke("query")
        """
        # Emit warning about GIL blocking
        warnings.warn(
            "Sync retrieval (_get_relevant_documents) blocks GIL in shared event loop. "
            "Use ainvoke() or _aget_relevant_documents() for async retrieval.",
            RuntimeWarning,
            stacklevel=2,
        )

        # Fallback to sync vectorstore methods (blocks GIL!)
        try:
            if self.search_type == "similarity":
                result = self.async_retriever.vectorstore.similarity_search(
                    query, **self.search_kwargs
                )
                return cast('list["Document"]', result)
            elif self.search_type == "mmr":
                result = self.async_retriever.vectorstore.max_marginal_relevance_search(
                    query, **self.search_kwargs
                )
                return cast('list["Document"]', result)
            else:
                # Should never happen (validated in __init__)
                raise ValueError(
                    f"Unknown search_type: {self.search_type}. "
                    f"Expected 'similarity' or 'mmr'."
                )
        except Exception as e:
            raise RuntimeError(
                f"Sync retrieval failed for query='{query[:50]}...': {e}"
            ) from e

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager: "AsyncCallbackManagerForRetrieverRun | None" = None,
    ) -> list["Document"]:
        """Asynchronous retrieval (GIL-free, RECOMMENDED).

        This method delegates to AsyncFAISSRetriever's async methods,
        which offload CPU-bound FAISS operations to a thread pool via
        asyncio.to_thread(), preventing GIL blocking in the main event loop.

        This is the recommended way to use AsyncFAISSVectorStoreRetriever
        in async contexts (e.g., FastAPI, Telegram bots, async LangChain chains).

        Args:
            query: Query text to search for
            run_manager: Optional async callback manager (unused)

        Returns:
            List of relevant documents

        Raises:
            ValueError: If search_type is invalid
            RuntimeError: If async retrieval fails

        Example:
            >>> lc_retriever = async_retriever.as_retriever(
            ...     search_type="similarity",
            ...     search_kwargs={"k": 5}
            ... )
            >>>
            >>> # ✅ Async, GIL-free
            >>> docs = await lc_retriever.ainvoke("python tutorial")
            >>> print(len(docs))
            5
            >>>
            >>> # Use in LangChain async chain
            >>> from langchain_core.runnables import RunnablePassthrough
            >>> chain = {
            ...     "context": lc_retriever,
            ...     "question": RunnablePassthrough()
            ... }
            >>> result = await chain.ainvoke("What is async?")
        """
        try:
            if self.search_type == "similarity":
                result = await self.async_retriever.similarity_search(
                    query, **self.search_kwargs
                )
                return cast('list["Document"]', result)
            elif self.search_type == "mmr":
                result = await self.async_retriever.max_marginal_relevance_search(
                    query, **self.search_kwargs
                )
                return cast('list["Document"]', result)
            else:
                # Should never happen (validated in __init__)
                raise ValueError(
                    f"Unknown search_type: {self.search_type}. "
                    f"Expected 'similarity' or 'mmr'."
                )
        except Exception as e:
            # Re-raise with context for better error messages
            raise RuntimeError(
                f"AsyncFAISSVectorStoreRetriever failed for query='{query[:50]}...': {e}"
            ) from e

    def __repr__(self) -> str:
        """User-friendly repr for debugging.

        Returns:
            String representation with key metadata

        Example:
            >>> lc_retriever = async_retriever.as_retriever(search_type="mmr")
            >>> print(repr(lc_retriever))
            AsyncFAISSVectorStoreRetriever(search_type=mmr, search_kwargs={'k': 4})
        """
        return (
            f"AsyncFAISSVectorStoreRetriever("
            f"search_type={self.search_type}, "
            f"search_kwargs={self.search_kwargs})"
        )
