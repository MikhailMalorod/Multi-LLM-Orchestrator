"""Unit tests for retrieval error classes."""

import pytest

from orchestrator.retrieval.errors import (
    DependencyError,
    InvalidQueryError,
    RetrieverError,
    ThreadPoolError,
    VectorStoreError,
)


class TestRetrieverErrors:
    """Test retrieval exception hierarchy."""

    def test_retriever_error_is_base(self):
        """Test RetrieverError is base exception."""
        with pytest.raises(RetrieverError):
            raise RetrieverError("Base error")

    def test_vector_store_error_inherits_retriever_error(self):
        """Test VectorStoreError inherits from RetrieverError."""
        with pytest.raises(RetrieverError):
            raise VectorStoreError("Vector store failed")

    def test_invalid_query_error_inherits_retriever_error(self):
        """Test InvalidQueryError inherits from RetrieverError."""
        with pytest.raises(RetrieverError):
            raise InvalidQueryError("Invalid query")

    def test_thread_pool_error_inherits_retriever_error(self):
        """Test ThreadPoolError inherits from RetrieverError."""
        with pytest.raises(RetrieverError):
            raise ThreadPoolError("Thread pool failed")

    def test_dependency_error_inherits_retriever_error(self):
        """Test DependencyError inherits from RetrieverError."""
        with pytest.raises(RetrieverError):
            raise DependencyError("Missing dependency")

    def test_dependency_error_default_message(self):
        """Test DependencyError has helpful default message."""
        error = DependencyError()

        error_msg = str(error)
        assert "faiss-cpu>=1.7.4" in error_msg
        assert "langchain-community>=0.0.38" in error_msg
        assert "pip install multi-llm-orchestrator[retrieval]" in error_msg

    def test_dependency_error_custom_message(self):
        """Test DependencyError accepts custom message."""
        custom_msg = "Custom dependency error"
        error = DependencyError(custom_msg)

        assert str(error) == custom_msg

    def test_all_errors_are_catchable_as_exception(self):
        """Test all error types are catchable as Exception."""
        errors = [
            RetrieverError("error"),
            VectorStoreError("error"),
            InvalidQueryError("error"),
            ThreadPoolError("error"),
            DependencyError("error"),
        ]

        for error in errors:
            with pytest.raises(Exception):  # noqa: B017
                raise error
