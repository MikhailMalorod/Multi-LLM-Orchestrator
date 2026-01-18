"""Unit tests for AsyncFAISSVectorStoreRetriever (LangChain compatibility)."""

import warnings

import pytest

from orchestrator.retrieval import AsyncFAISSRetriever


class TestAsyncFAISSVectorStoreRetriever:
    """Test LangChain compatibility layer."""

    async def test_as_retriever_factory_method(self, small_faiss_index):
        """Test as_retriever() creates AsyncFAISSVectorStoreRetriever."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)

        lc_retriever = async_retriever.as_retriever(
            search_type="similarity", search_kwargs={"k": 5}
        )

        # Check type (avoid importing to prevent circular deps)
        assert lc_retriever.__class__.__name__ == "AsyncFAISSVectorStoreRetriever"
        assert lc_retriever.async_retriever is async_retriever
        assert lc_retriever.search_type == "similarity"
        assert lc_retriever.search_kwargs == {"k": 5}

    async def test_as_retriever_default_params(self, small_faiss_index):
        """Test as_retriever() with default parameters."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)

        lc_retriever = async_retriever.as_retriever()

        assert lc_retriever.search_type == "similarity"
        assert lc_retriever.search_kwargs == {}

    async def test_ainvoke_similarity(self, small_faiss_index):
        """Test async invoke with similarity search."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(
            search_type="similarity", search_kwargs={"k": 5}
        )

        docs = await lc_retriever.ainvoke("test query")

        assert len(docs) == 5
        assert all(hasattr(doc, "page_content") for doc in docs)

    async def test_ainvoke_mmr(self, small_faiss_index):
        """Test async invoke with MMR search."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(
            search_type="mmr", search_kwargs={"k": 5, "lambda_mult": 0.7}
        )

        docs = await lc_retriever.ainvoke("test query")

        assert len(docs) == 5

    async def test_ainvoke_with_filter(self, small_faiss_index):
        """Test async invoke with metadata filter."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(
            search_type="similarity", search_kwargs={"k": 10, "filter": {"topic": 1}}
        )

        docs = await lc_retriever.ainvoke("test query")

        assert len(docs) > 0
        for doc in docs:
            assert doc.metadata.get("topic") == 1

    def test_invoke_sync_warning(self, small_faiss_index):
        """Test sync invoke emits RuntimeWarning about GIL blocking."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(search_kwargs={"k": 3})

        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            docs = lc_retriever.invoke("test query")

            # Check warning was emitted
            assert len(w) == 1
            assert issubclass(w[0].category, RuntimeWarning)
            assert "blocks GIL" in str(w[0].message)

        # Check results are still correct
        assert len(docs) == 3

    def test_invoke_sync_mmr(self, small_faiss_index):
        """Test sync invoke with MMR search type."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(
            search_type="mmr", search_kwargs={"k": 5}
        )

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            docs = lc_retriever.invoke("test query")

        assert len(docs) == 5

    async def test_search_type_validation(self, small_faiss_index):
        """Test ValueError for invalid search_type."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)

        with pytest.raises(
            ValueError, match="search_type must be 'similarity' or 'mmr'"
        ):
            async_retriever.as_retriever(search_type="invalid")  # type: ignore[arg-type]

    async def test_search_type_case_sensitive(self, small_faiss_index):
        """Test search_type is case-sensitive."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)

        with pytest.raises(ValueError):
            async_retriever.as_retriever(search_type="Similarity")  # type: ignore[arg-type]

        with pytest.raises(ValueError):
            async_retriever.as_retriever(search_type="MMR")  # type: ignore[arg-type]

    async def test_repr(self, small_faiss_index):
        """Test __repr__ returns user-friendly string."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(
            search_type="mmr", search_kwargs={"k": 10, "lambda_mult": 0.5}
        )

        repr_str = repr(lc_retriever)

        assert "AsyncFAISSVectorStoreRetriever" in repr_str
        assert "search_type=mmr" in repr_str
        assert "search_kwargs=" in repr_str

    async def test_error_propagation_async(self, mock_faiss_vectorstore):
        """Test RuntimeError propagation in async invoke."""
        # Make similarity_search raise an exception

        async_retriever = AsyncFAISSRetriever(mock_faiss_vectorstore)

        # Override similarity_search to raise
        async def failing_search(*args, **kwargs):
            raise ValueError("Test error")

        async_retriever.similarity_search = failing_search  # type: ignore[method-assign]

        lc_retriever = async_retriever.as_retriever(search_type="similarity")

        with pytest.raises(RuntimeError, match="AsyncFAISSVectorStoreRetriever failed"):
            await lc_retriever.ainvoke("query")

    def test_error_propagation_sync(self, mock_faiss_vectorstore):
        """Test RuntimeError propagation in sync invoke."""
        # Make similarity_search raise an exception
        mock_faiss_vectorstore.similarity_search.side_effect = ValueError("Test error")

        async_retriever = AsyncFAISSRetriever(mock_faiss_vectorstore)
        lc_retriever = async_retriever.as_retriever(search_type="similarity")

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            with pytest.raises(RuntimeError, match="Sync retrieval failed"):
                lc_retriever.invoke("query")

    async def test_concurrent_ainvoke(self, small_faiss_index):
        """Test concurrent async invocations."""
        import asyncio

        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(search_kwargs={"k": 3})

        # Run 5 concurrent invokes
        queries = [f"query {i}" for i in range(5)]
        tasks = [lc_retriever.ainvoke(q) for q in queries]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(len(docs) == 3 for docs in results)

    async def test_search_kwargs_empty_dict(self, small_faiss_index):
        """Test as_retriever with empty search_kwargs."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(
            search_type="similarity", search_kwargs={}
        )

        # Should use default k=4 from BaseAsyncRetriever
        docs = await lc_retriever.ainvoke("query")

        # FAISS default k is 4
        assert len(docs) == 4

    async def test_search_kwargs_override_defaults(self, small_faiss_index):
        """Test search_kwargs override method defaults."""
        async_retriever = AsyncFAISSRetriever(small_faiss_index)
        lc_retriever = async_retriever.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 3, "fetch_k": 15, "lambda_mult": 0.8},
        )

        docs = await lc_retriever.ainvoke("query")

        assert len(docs) == 3  # Respects custom k
