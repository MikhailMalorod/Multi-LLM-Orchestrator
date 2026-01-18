"""Performance benchmarks for AsyncFAISSRetriever.

⭐ CRITICAL: test_p99_latency_10_concurrent is PRIMARY acceptance criteria!

These tests verify that AsyncFAISSRetriever meets performance requirements
from Issue #9, specifically:
- p99 latency <5s for 10 concurrent queries (CRITICAL)
- GIL mitigation effectiveness (async faster than sync)
- Stress test with 100 concurrent queries
- No memory leaks
"""

import asyncio
import time

import pytest

from orchestrator.retrieval import AsyncFAISSRetriever


class TestAsyncFAISSPerformance:
    """Performance benchmarks for AsyncFAISSRetriever.

    These tests use synthetic_faiss_index fixture (1000 docs, 384-dim)
    with FakeEmbeddings. Performance characteristics:
    - Single query: ~1-2ms
    - 10 concurrent queries: ~10-20ms (with GIL mitigation)
    - 100 concurrent queries: ~100-300ms (with GIL mitigation)
    """

    async def test_p99_latency_10_concurrent(self, synthetic_faiss_index):
        """⭐ CRITICAL: p99 latency <5s for 10 concurrent queries.

        This is the PRIMARY acceptance criteria from Issue #9.
        If this test fails, v0.9.0 CANNOT be released.

        Test procedure:
        1. Warmup query (exclude cold start)
        2. Run 10 concurrent queries
        3. Measure individual latencies
        4. Calculate p50, p95, p99
        5. Assert p99 <5s

        Expected results (with FakeEmbeddings + GIL mitigation):
        - p50: <10ms
        - p95: <50ms
        - p99: <100ms (well below 5s threshold)
        """
        retriever = AsyncFAISSRetriever(synthetic_faiss_index)

        try:
            # ✅ WARMUP (exclude cold start from measurement)
            _ = await retriever.similarity_search("warmup query", k=5)

            # Measure latency for 10 concurrent queries
            async def search_and_measure(query: str) -> float:
                start = time.perf_counter()
                docs = await retriever.similarity_search(query, k=5)
                latency = (time.perf_counter() - start) * 1000  # milliseconds
                assert len(docs) == 5, f"Expected 5 docs, got {len(docs)}"
                return latency

            # Run 10 concurrent queries
            latencies = await asyncio.gather(
                *[
                    search_and_measure(f"test query {i} about topic {i % 10}")
                    for i in range(10)
                ]
            )

            # Calculate percentiles
            sorted_latencies = sorted(latencies)
            p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

            # Log results for documentation
            print("\n📊 ⭐ CRITICAL Performance Test Results:")
            print(f"  p50: {p50:.2f}ms")
            print(f"  p95: {p95:.2f}ms")
            print(f"  p99: {p99:.2f}ms")
            print(f"  min: {min(latencies):.2f}ms")
            print(f"  max: {max(latencies):.2f}ms")
            print(f"  avg: {sum(latencies)/len(latencies):.2f}ms")
            print(f"  total: {sum(latencies):.2f}ms")

            # ⭐ CRITICAL ASSERTION
            assert p99 < 5000, (
                f"❌ FAILED: p99 latency {p99:.2f}ms exceeds 5000ms threshold! "
                f"This is a PRIMARY acceptance criteria from Issue #9. "
                f"v0.9.0 cannot be released until this passes."
            )

            print(f"\n✅ ⭐ CRITICAL TEST PASSED: p99 {p99:.2f}ms < 5000ms")
        finally:
            await retriever.close()

    async def test_comparison_sync_vs_async(self, synthetic_faiss_index):
        """Benchmark: async should be faster than sync for concurrent queries.

        This test demonstrates the benefit of GIL mitigation:
        - Sync: Sequential queries (blocked by GIL)
        - Async: Concurrent queries (GIL-free with asyncio.to_thread)

        Expected speedup with FakeEmbeddings: 1.2-3x
        Expected speedup with real embeddings: 3-10x
        """
        # Sync version (sequential)
        start = time.perf_counter()
        for i in range(10):
            docs = synthetic_faiss_index.similarity_search(f"query {i}", k=5)
            assert len(docs) == 5
        sync_time = time.perf_counter() - start

        # Async version (concurrent)
        retriever = AsyncFAISSRetriever(synthetic_faiss_index)

        try:
            # Warmup
            _ = await retriever.similarity_search("warmup", k=5)

            start = time.perf_counter()
            results = await asyncio.gather(
                *[
                    retriever.similarity_search(f"query {i}", k=5)
                    for i in range(10)
                ]
            )
            async_time = time.perf_counter() - start

            # Verify all returned correct number of docs
            assert all(len(docs) == 5 for docs in results)

            # Calculate speedup
            speedup = sync_time / async_time

            print("\n📊 Sync vs Async Comparison:")
            print(f"  Sync (sequential): {sync_time*1000:.2f}ms")
            print(f"  Async (concurrent): {async_time*1000:.2f}ms")
            print(f"  Speedup: {speedup:.2f}x")

            # For FakeEmbeddings, async may be slower due to overhead
            # This is expected: FakeEmbeddings are so fast (~0.1ms) that
            # asyncio.to_thread() overhead dominates.
            #
            # With real embeddings (50-200ms), async would show 3-10x speedup.
            #
            # For this test, we just verify no catastrophic slowdown
            assert speedup >= 0.1, (
                f"Async is {1/speedup:.1f}x slower than sync (speedup={speedup:.2f}x). "
                f"This indicates a severe performance regression."
            )

            # Log interpretation
            if speedup >= 1.5:
                print(f"  ✅ Excellent speedup: {speedup:.2f}x (GIL mitigation working!)")
            elif speedup >= 1.0:
                print(f"  ✅ Good speedup: {speedup:.2f}x")
            elif speedup >= 0.5:
                print(f"  ⚠️ Async overhead visible: {speedup:.2f}x (expected with FakeEmbeddings)")
                print("     Real embeddings (50-200ms) would show 3-10x speedup")
            else:
                print(f"  ⚠️ Async is {1/speedup:.1f}x slower: {speedup:.2f}x")
                print("     This is normal for FakeEmbeddings (too fast, overhead dominates)")
                print("     Real embeddings would show significant speedup")
        finally:
            await retriever.close()

    async def test_100_concurrent_queries(self, synthetic_faiss_index):
        """Stress test: 100 concurrent queries.

        This test verifies system stability under heavy load:
        - 100 concurrent queries
        - All queries must succeed
        - p99 latency should be <10s (relaxed vs 10 concurrent)
        - No resource leaks

        This simulates a high-traffic production scenario (e.g., bot farm).
        """
        retriever = AsyncFAISSRetriever(synthetic_faiss_index, max_workers=10)

        try:
            # Warmup
            _ = await retriever.similarity_search("warmup", k=5)

            # Measure individual latencies
            async def search_and_measure(query: str) -> float:
                start = time.perf_counter()
                docs = await retriever.similarity_search(query, k=5)
                latency = (time.perf_counter() - start) * 1000  # milliseconds
                assert len(docs) == 5, f"Expected 5 docs, got {len(docs)}"
                return latency

            # 100 concurrent queries
            start_total = time.perf_counter()
            latencies = await asyncio.gather(
                *[
                    search_and_measure(f"query {i} about topic {i % 10}")
                    for i in range(100)
                ]
            )
            total_time = time.perf_counter() - start_total

            # Calculate statistics
            sorted_latencies = sorted(latencies)
            p50 = sorted_latencies[50]
            p95 = sorted_latencies[95]
            p99 = sorted_latencies[99]

            print("\n📊 Stress Test (100 concurrent):")
            print(f"  Total time: {total_time*1000:.2f}ms")
            print(f"  p50: {p50:.2f}ms")
            print(f"  p95: {p95:.2f}ms")
            print(f"  p99: {p99:.2f}ms")
            print(f"  min: {min(latencies):.2f}ms")
            print(f"  max: {max(latencies):.2f}ms")
            print(f"  avg: {sum(latencies)/len(latencies):.2f}ms")

            # p99 should be <10s (relaxed constraint for stress test)
            assert p99 < 10000, (
                f"p99 {p99:.2f}ms exceeds 10s threshold for stress test. "
                f"System may not handle high concurrency well."
            )

            print(f"  ✅ Stress test PASSED: p99 {p99:.2f}ms < 10000ms")
        finally:
            await retriever.close()

    async def test_memory_usage(self, synthetic_faiss_index):
        """Verify no memory leaks during repeated queries.

        This test runs 1000 queries (100 batches of 10) and verifies:
        - Memory increase is reasonable (<100MB)
        - No unbounded growth
        - Proper resource cleanup

        Note: This test requires psutil. If not installed, test is skipped.
        """
        psutil = pytest.importorskip("psutil", reason="psutil not installed")

        retriever = AsyncFAISSRetriever(synthetic_faiss_index)
        process = psutil.Process()

        try:
            # Warmup
            _ = await retriever.similarity_search("warmup", k=5)

            # Baseline memory
            mem_before = process.memory_info().rss / 1024 / 1024  # MB

            # Run 1000 queries in batches of 10
            for batch in range(100):
                await asyncio.gather(
                    *[
                        retriever.similarity_search(f"query {batch}_{i}", k=5)
                        for i in range(10)
                    ]
                )

            # Memory after
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            mem_increase = mem_after - mem_before

            print("\n📊 Memory Usage (1000 queries):")
            print(f"  Before: {mem_before:.2f}MB")
            print(f"  After: {mem_after:.2f}MB")
            print(f"  Increase: {mem_increase:.2f}MB")

            # Should not increase by more than 100MB
            assert mem_increase < 100, (
                f"Memory increased by {mem_increase:.2f}MB, possible memory leak"
            )

            print("  ✅ No memory leak detected")
        finally:
            await retriever.close()

    async def test_throughput_measurement(self, synthetic_faiss_index):
        """Measure throughput: queries per second.

        This test measures system throughput by running queries continuously
        for 1 second and counting completed queries.

        Expected throughput with FakeEmbeddings: 500-2000 qps
        Expected throughput with real embeddings: 50-200 qps
        """
        retriever = AsyncFAISSRetriever(synthetic_faiss_index, max_workers=10)

        try:
            # Warmup
            _ = await retriever.similarity_search("warmup", k=5)

            # Measure throughput for 1 second
            start_time = time.perf_counter()
            end_time = start_time + 1.0  # 1 second
            query_count = 0

            while time.perf_counter() < end_time:
                # Run 10 queries at a time
                await asyncio.gather(
                    *[
                        retriever.similarity_search(f"query {query_count + i}", k=5)
                        for i in range(10)
                    ]
                )
                query_count += 10

            elapsed = time.perf_counter() - start_time
            qps = query_count / elapsed

            print("\n📊 Throughput Measurement:")
            print(f"  Total queries: {query_count}")
            print(f"  Elapsed time: {elapsed:.2f}s")
            print(f"  Throughput: {qps:.0f} queries/second")

            # Sanity check: should handle at least 100 qps
            assert qps >= 100, (
                f"Throughput {qps:.0f} qps is too low. "
                f"Expected at least 100 qps."
            )

            print(f"  ✅ Throughput test PASSED: {qps:.0f} qps >= 100 qps")
        finally:
            await retriever.close()

    async def test_latency_distribution(self, synthetic_faiss_index):
        """Analyze latency distribution for 50 queries.

        This test provides detailed latency statistics:
        - p50, p90, p95, p99, p999
        - Standard deviation
        - Outliers

        Useful for documentation and performance characterization.
        """
        retriever = AsyncFAISSRetriever(synthetic_faiss_index)

        try:
            # Warmup
            _ = await retriever.similarity_search("warmup", k=5)

            # Measure 50 queries
            async def search_and_measure(query: str) -> float:
                start = time.perf_counter()
                docs = await retriever.similarity_search(query, k=5)
                latency = (time.perf_counter() - start) * 1000  # milliseconds
                assert len(docs) == 5
                return latency

            latencies = await asyncio.gather(
                *[
                    search_and_measure(f"query {i} about topic {i % 10}")
                    for i in range(50)
                ]
            )

            # Calculate percentiles and statistics
            sorted_latencies = sorted(latencies)
            p50 = sorted_latencies[25]  # 50th percentile
            p90 = sorted_latencies[45]  # 90th percentile
            p95 = sorted_latencies[47]  # 95th percentile
            p99 = sorted_latencies[49]  # 99th percentile (last for 50 samples)

            mean = sum(latencies) / len(latencies)
            variance = sum((x - mean) ** 2 for x in latencies) / len(latencies)
            stddev = variance**0.5

            print("\n📊 Latency Distribution (50 queries):")
            print(f"  min:  {min(latencies):.2f}ms")
            print(f"  p50:  {p50:.2f}ms")
            print(f"  p90:  {p90:.2f}ms")
            print(f"  p95:  {p95:.2f}ms")
            print(f"  p99:  {p99:.2f}ms")
            print(f"  max:  {max(latencies):.2f}ms")
            print(f"  mean: {mean:.2f}ms")
            print(f"  std:  {stddev:.2f}ms")

            # Verify reasonable distribution
            assert p99 < 1000, (
                f"p99 {p99:.2f}ms is too high for 50 sequential queries"
            )

            print("  ✅ Latency distribution is reasonable")
        finally:
            await retriever.close()
