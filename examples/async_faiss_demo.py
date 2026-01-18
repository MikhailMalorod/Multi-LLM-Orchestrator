"""Demo: AsyncFAISSRetriever with synthetic FAISS index.

This example demonstrates core AsyncFAISSRetriever functionality:
- Basic similarity search
- Search with relevance scores
- MMR (diversity-aware) search
- Metadata filters (dict + callable)
- Concurrent queries with asyncio.gather

Requirements:
    pip install multi-llm-orchestrator[retrieval]
"""

import asyncio
import time

from langchain_community.embeddings import FakeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from orchestrator.retrieval import AsyncFAISSRetriever


async def main():
    print("=" * 60)
    print("AsyncFAISSRetriever Demo")
    print("=" * 60)

    # ========================================================================
    # Step 1: Create synthetic FAISS index
    # ========================================================================
    print("\n[1/6] Creating FAISS index (100 docs, 384-dim)...")
    embeddings = FakeEmbeddings(size=384)

    docs = [
        Document(
            page_content=f"Document {i} about topic {i % 5}. "
            f"This document contains information on subject matter {i % 5}.",
            metadata={"id": i, "topic": i % 5, "group": i // 20},
        )
        for i in range(100)
    ]

    vectorstore = FAISS.from_documents(docs, embeddings)
    print(f"✓ Created FAISS index with {vectorstore.index.ntotal} documents")

    # ========================================================================
    # Step 2: Wrap in AsyncFAISSRetriever
    # ========================================================================
    print("\n[2/6] Initializing AsyncFAISSRetriever...")
    retriever = AsyncFAISSRetriever(vectorstore)

    # Get vectorstore info
    info = retriever.get_vectorstore_info()
    print(
        f"✓ Initialized retriever: {info['index_size']} docs, "
        f"{info['dimension']}-dim, executor={info['executor_type']}"
    )

    try:
        # ====================================================================
        # Step 3: Basic similarity search
        # ====================================================================
        print("\n[3/6] Basic similarity search (k=5)...")
        results = await retriever.similarity_search("topic 3", k=5)

        print(f"✓ Found {len(results)} documents:")
        for i, doc in enumerate(results, 1):
            topic = doc.metadata.get("topic", "N/A")
            print(f"  {i}. Topic {topic}: {doc.page_content[:50]}...")

        # ====================================================================
        # Step 4: Search with scores
        # ====================================================================
        print("\n[4/6] Search with relevance scores (k=3)...")
        results_with_scores = await retriever.similarity_search_with_score(
            "topic 3", k=3
        )

        print(f"✓ Found {len(results_with_scores)} documents with scores:")
        for i, (doc, score) in enumerate(results_with_scores, 1):
            topic = doc.metadata.get("topic", "N/A")
            print(
                f"  {i}. Topic {topic}, Score {score:.4f}: {doc.page_content[:40]}..."
            )

        # ====================================================================
        # Step 5: MMR search (diversity-aware)
        # ====================================================================
        print("\n[5/6] MMR search - diversity-aware (k=5, lambda=0.5)...")
        mmr_docs = await retriever.max_marginal_relevance_search(
            "topic 3", k=5, lambda_mult=0.5
        )

        print(f"✓ Found {len(mmr_docs)} diverse documents:")
        topics_found = [doc.metadata.get("topic") for doc in mmr_docs]
        unique_topics = len(set(topics_found))
        print(f"  Topics distribution: {topics_found}")
        print(f"  Unique topics: {unique_topics}/5 (higher = more diverse)")

        # ====================================================================
        # Step 6: Metadata filters
        # ====================================================================
        print("\n[6/6] Metadata filters...")

        # Dict filter: topic=2
        print("  a) Dict filter: topic=2")
        filtered_docs = await retriever.similarity_search(
            "document", k=10, filter={"topic": 2}
        )
        print(f"     ✓ Found {len(filtered_docs)} documents with topic=2")
        for doc in filtered_docs[:3]:
            assert doc.metadata["topic"] == 2

        # Callable filter: group >= 2
        def filter_func(metadata: dict) -> bool:
            return metadata.get("group", 0) >= 2

        print("  b) Callable filter: group >= 2")
        filtered_docs = await retriever.similarity_search(
            "document", k=10, filter=filter_func, fetch_k=50
        )
        print(f"     ✓ Found {len(filtered_docs)} documents with group >= 2")
        for doc in filtered_docs[:3]:
            assert doc.metadata["group"] >= 2

        # ====================================================================
        # BONUS: Concurrent queries (stress test)
        # ====================================================================
        print("\n[BONUS] Concurrent queries stress test (10 parallel)...")

        start_time = time.perf_counter()
        queries = [f"topic {i}" for i in range(10)]
        tasks = [retriever.similarity_search(q, k=5) for q in queries]
        concurrent_results = await asyncio.gather(*tasks)
        elapsed = (time.perf_counter() - start_time) * 1000  # milliseconds

        print(f"✓ Completed {len(concurrent_results)} queries in {elapsed:.2f}ms")
        print(
            f"  Average: {elapsed/len(concurrent_results):.2f}ms per query"
        )
        print(f"  Throughput: ~{1000/elapsed*len(concurrent_results):.0f} qps")

        # Verify all returned correct count
        assert all(len(docs) == 5 for docs in concurrent_results)

    finally:
        # Always cleanup
        await retriever.close()
        print("\n✓ Retriever closed")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
