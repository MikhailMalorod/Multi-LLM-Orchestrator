"""Demo: AsyncFAISSRetriever with LangChain integration.

This example demonstrates LangChain integration:
- Converting AsyncFAISSRetriever to BaseRetriever
- Using in LangChain chains (RetrievalQA)
- Async invoke vs sync invoke
- RAG pipeline with mock LLM

Requirements:
    pip install multi-llm-orchestrator[retrieval]

Note: This demo uses MockProvider instead of real LLM for demonstration.
      In production, replace with ChatOpenAI, ChatAnthropic, etc.
"""

import asyncio
import warnings

from langchain_community.embeddings import FakeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.language_models.llms import LLM

from orchestrator.retrieval import AsyncFAISSRetriever


# ============================================================================
# Mock LLM for demonstration (replace with real LLM in production)
# ============================================================================
class MockLLM(LLM):
    """Mock LLM that returns canned responses for demonstration."""

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _call(
        self,
        prompt: str,
        stop: list[str] | None = None,
        **kwargs,
    ) -> str:
        """Return mock response based on prompt."""
        if "Python" in prompt:
            return (
                "Based on the retrieved documents, Python is a programming "
                "language commonly used for data science."
            )
        return (
            "Based on the retrieved documents, here is a summary of the information."
        )


async def main():
    print("=" * 60)
    print("AsyncFAISSRetriever + LangChain Integration Demo")
    print("=" * 60)

    # ========================================================================
    # Step 1: Create FAISS index with sample documents
    # ========================================================================
    print("\n[1/5] Creating FAISS index...")
    embeddings = FakeEmbeddings(size=384)

    docs = [
        Document(
            page_content="Python is a high-level programming language known for its simplicity.",
            metadata={"source": "doc1.txt", "topic": "python"},
        ),
        Document(
            page_content="Python is widely used in data science and machine learning.",
            metadata={"source": "doc2.txt", "topic": "python"},
        ),
        Document(
            page_content="JavaScript is a programming language primarily used for web development.",
            metadata={"source": "doc3.txt", "topic": "javascript"},
        ),
        Document(
            page_content="Rust is a systems programming language focused on safety and performance.",
            metadata={"source": "doc4.txt", "topic": "rust"},
        ),
        Document(
            page_content="Data science involves extracting insights from data using statistical methods.",
            metadata={"source": "doc5.txt", "topic": "data_science"},
        ),
    ]

    vectorstore = FAISS.from_documents(docs, embeddings)
    print(f"✓ Created FAISS index with {len(docs)} documents")

    # ========================================================================
    # Step 2: Create AsyncFAISSRetriever and convert to LangChain retriever
    # ========================================================================
    print("\n[2/5] Converting to LangChain BaseRetriever...")
    async_retriever = AsyncFAISSRetriever(vectorstore)

    # Convert to LangChain-compatible retriever
    lc_retriever = async_retriever.as_retriever(
        search_type="similarity", search_kwargs={"k": 3}
    )

    print(f"✓ Created LangChain retriever: {type(lc_retriever).__name__}")
    print(f"  Search type: similarity")
    print(f"  Search kwargs: k=3")

    # ========================================================================
    # Step 3: Use async invoke (RECOMMENDED)
    # ========================================================================
    print("\n[3/5] Using async invoke (RECOMMENDED - GIL-free)...")

    query = "What is Python?"
    docs_retrieved = await lc_retriever.ainvoke(query)

    print(f"✓ Retrieved {len(docs_retrieved)} documents for '{query}':")
    for i, doc in enumerate(docs_retrieved, 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:60]}...")

    # ========================================================================
    # Step 4: Use sync invoke (NOT RECOMMENDED - blocks GIL)
    # ========================================================================
    print("\n[4/5] Using sync invoke (NOT RECOMMENDED - blocks GIL)...")
    print("  ⚠️  This will emit a RuntimeWarning about GIL blocking")

    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Call sync method (blocks GIL!)
        docs_sync = lc_retriever.invoke(query)

        # Check if warning was emitted
        if w:
            runtime_warnings = [
                warn for warn in w if issubclass(warn.category, RuntimeWarning)
            ]
            if runtime_warnings:
                print(f"  ✓ RuntimeWarning emitted as expected:")
                print(f"    '{runtime_warnings[0].message}'")

    print(f"✓ Retrieved {len(docs_sync)} documents (sync)")

    # ========================================================================
    # Step 5: Use in RAG chain
    # ========================================================================
    print("\n[5/5] Using in RAG chain (RetrievalQA)...")

    # Create mock LLM
    llm = MockLLM()

    # Create RAG chain
    from langchain.chains import RetrievalQA

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=lc_retriever,
        return_source_documents=True,
    )

    # Query the chain
    print(f"  Query: '{query}'")
    result = await chain.ainvoke(query)

    print(f"\n  LLM Response:")
    print(f"  {result['result']}")

    print(f"\n  Source Documents:")
    for i, doc in enumerate(result["source_documents"], 1):
        print(f"  {i}. [{doc.metadata['source']}] {doc.page_content[:50]}...")

    # ========================================================================
    # BONUS: MMR search type
    # ========================================================================
    print("\n[BONUS] MMR search type (diversity-aware)...")

    # Create MMR retriever
    mmr_retriever = async_retriever.as_retriever(
        search_type="mmr", search_kwargs={"k": 3, "lambda_mult": 0.5}
    )

    mmr_docs = await mmr_retriever.ainvoke("programming language")

    print(f"✓ Retrieved {len(mmr_docs)} diverse documents:")
    topics = [doc.metadata.get("topic") for doc in mmr_docs]
    print(f"  Topics: {topics}")
    print(f"  Unique topics: {len(set(topics))}/3 (higher = more diverse)")

    # ========================================================================
    # Cleanup
    # ========================================================================
    await async_retriever.close()
    print("\n✓ Retriever closed")

    print("\n" + "=" * 60)
    print("LangChain integration demo completed!")
    print("\n💡 Key Takeaways:")
    print("  1. Use ainvoke() for async, GIL-free retrieval")
    print("  2. Avoid invoke() - it blocks the GIL")
    print("  3. Works seamlessly with LangChain chains")
    print("  4. Supports both similarity and MMR search types")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
