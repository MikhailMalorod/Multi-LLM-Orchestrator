"""Async retrieval module for vector stores.

This module provides AsyncFAISSRetriever with GIL mitigation for
Shared Bot Pool architectures (e.g., Telegram bot farms, FastAPI RAG endpoints).

The module uses optional dependency pattern - faiss-cpu and langchain-community
must be installed via: pip install multi-llm-orchestrator[retrieval]

Example:
    >>> from orchestrator.retrieval import AsyncFAISSRetriever
    >>> from langchain_community.vectorstores import FAISS
    >>>
    >>> # Create FAISS vectorstore
    >>> vectorstore = FAISS.from_documents(docs, embeddings)
    >>>
    >>> # Wrap in AsyncFAISSRetriever for GIL-free retrieval
    >>> retriever = AsyncFAISSRetriever(vectorstore)
    >>>
    >>> # Async search (concurrent queries don't block each other)
    >>> docs = await retriever.similarity_search("query", k=5)
"""

from .base import BaseAsyncRetriever
from .errors import (
    DependencyError,
    InvalidQueryError,
    RetrieverError,
    ThreadPoolError,
    VectorStoreError,
)

# Try to import AsyncFAISSRetriever (requires optional dependencies)
try:
    from .async_faiss import AsyncFAISSRetriever

    FAISS_AVAILABLE = True

    __all__ = [
        "AsyncFAISSRetriever",
        "BaseAsyncRetriever",
        "RetrieverError",
        "VectorStoreError",
        "InvalidQueryError",
        "ThreadPoolError",
        "DependencyError",
    ]
except ImportError:
    # faiss-cpu or langchain-community not installed
    FAISS_AVAILABLE = False

    __all__ = [
        "BaseAsyncRetriever",
        "RetrieverError",
        "VectorStoreError",
        "InvalidQueryError",
        "ThreadPoolError",
        "DependencyError",
    ]
