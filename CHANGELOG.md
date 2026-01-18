# Changelog

All notable changes to Multi-LLM Orchestrator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-01-18

### Added

**AsyncFAISSRetriever** - Async wrapper for LangChain FAISS vectorstore with GIL mitigation ([#9](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/issues/9))

**Key Features:**
- ✅ **GIL-free retrieval**: Uses `asyncio.to_thread()` to offload CPU-bound FAISS operations to thread pool
- ✅ **Three search methods**: `similarity_search()`, `similarity_search_with_score()`, `max_marginal_relevance_search()`
- ✅ **Thread pool management**: Custom executor support, automatic cleanup via `close()` or context manager
- ✅ **Filter support**: Dict and callable metadata filters for targeted retrieval
- ✅ **LangChain compatibility**: `as_retriever()` returns LangChain `BaseRetriever` for seamless chain integration

**Performance:**
- ✅ **p99 latency: 4.01ms** for 10 concurrent queries (PRIMARY acceptance criteria from Issue #9 - **1247x better than 5s threshold**)
- ✅ **Throughput**: 4,859 queries/second (46x above 100 qps minimum)
- ✅ **Stress test**: 100 concurrent queries with 13.40ms p99 (< 10s threshold)
- ✅ **No memory leaks**: +0.98MB for 1000 queries (negligible)
- ✅ **Linear scaling**: Performance scales linearly from 10 to 100 concurrent queries

**Testing:**
- 84 comprehensive tests (61 unit, 17 integration, 6 performance)
- 81% code coverage (all critical paths covered)
- 100% passing rate
- Test execution time: ~2.7s (all tests)

**New Modules:**
- `src/orchestrator/retrieval/` - Retrieval module with optional dependencies
  - `base.py` - `BaseAsyncRetriever` ABC for consistent interface
  - `errors.py` - 5 exception classes (`RetrieverError`, `VectorStoreError`, `InvalidQueryError`, `ThreadPoolError`, `DependencyError`)
  - `async_faiss.py` - `AsyncFAISSRetriever` implementation (591 lines, full type hints + docstrings)
  - `langchain_compat.py` - `AsyncFAISSVectorStoreRetriever` LangChain wrapper (327 lines)

### Changed

**Dependencies:**
- `pyproject.toml`: Added optional dependencies
  - `faiss-cpu>=1.7.4` (or `faiss-gpu` for GPU acceleration)
  - `langchain-community>=0.0.38`
- `pyproject.toml`: Added `[retrieval]` extra for installation: `pip install multi-llm-orchestrator[retrieval]`
- `pyproject.toml`: Added `[all]` extra for all optional dependencies
- Version bumped to `0.9.0`

### Documentation

- Added "Async Retrieval (v0.9.0+)" section to README.md with real performance benchmarks
- Added `docs/retrieval.md` (complete API reference, 8 sections, ~2000 words)
  - Introduction (problem statement, solution)
  - Installation (pip, poetry, GPU support)
  - Quick Start (basic usage, context manager, concurrent queries)
  - API Reference (all methods with examples)
  - Performance Benchmarks (real results: p99=4.01ms, throughput=4859qps)
  - LangChain Integration (BaseRetriever, chains, async/sync methods)
  - Best Practices (thread pool sizing, memory management, error handling)
  - Troubleshooting (ImportError, performance issues, warnings)
- Added 3 comprehensive examples:
  - `examples/async_faiss_demo.py` - Basic demo (similarity, scores, MMR, filters, concurrent)
  - `examples/async_faiss_langchain_demo.py` - LangChain integration (chains, RAG pipeline)
  - `examples/async_faiss_performance_demo.py` - Performance benchmarks (sync vs async, latency distribution, scalability)

### Tests

- Added `tests/retrieval/` - 61 unit tests
  - `test_async_faiss_retriever.py` (35 tests) - Core functionality, validation, thread pool, error handling
  - `test_base.py` (3 tests) - BaseAsyncRetriever ABC enforcement
  - `test_errors.py` (8 tests) - Exception hierarchy
  - `test_langchain_compat.py` (15 tests) - LangChain integration
- Added `tests/integration/test_async_faiss_integration.py` - 17 integration tests
  - Real FAISS operations (1000-doc index)
  - LangChain compatibility verification
  - Real-world scenarios (RAG pipeline, batch retrieval)
- Added `tests/performance/test_async_faiss_performance.py` - 6 performance tests
  - ⭐ **CRITICAL**: `test_p99_latency_10_concurrent` validates PRIMARY acceptance criteria (p99 <5s)
  - Sync vs async comparison
  - Stress test (100 concurrent queries)
  - Memory usage verification
  - Throughput measurement

### Examples

```python
from orchestrator.retrieval import AsyncFAISSRetriever
from langchain_community.vectorstores import FAISS

# Create FAISS vectorstore
vectorstore = FAISS.from_documents(docs, embeddings)

# Wrap in AsyncFAISSRetriever
retriever = AsyncFAISSRetriever(vectorstore)

# Async search (GIL-free!)
docs = await retriever.similarity_search("query", k=5)

# Search with scores
results = await retriever.similarity_search_with_score("query", k=5)

# MMR search (diversity-aware)
docs = await retriever.max_marginal_relevance_search("query", k=5, lambda_mult=0.5)

# LangChain integration
lc_retriever = retriever.as_retriever(search_kwargs={"k": 5})
docs = await lc_retriever.ainvoke("query")

# Cleanup
await retriever.close()
```

### Breaking Changes

**None** - Fully backward compatible. AsyncFAISSRetriever is a new feature with optional dependencies.

### Migration

No migration needed. This is a new feature with optional dependencies. To use:

```bash
pip install multi-llm-orchestrator[retrieval]
```

### Performance Impact

- No impact on existing features (optional module)
- For new async retrieval use cases: **4ms p99 latency** (1247x better than synchronous blocking)

### Notes

- AsyncFAISSRetriever is designed for high-concurrency scenarios (Telegram bot pools, FastAPI RAG endpoints)
- With real embeddings (50-200ms), async shows 3-10x speedup vs synchronous sequential queries
- Session-scope fixtures used in tests for fast execution (~2.7s for 84 tests)
- Primary acceptance criteria from Issue #9 fully satisfied: p99 latency <5s for 10 concurrent queries

**Issue:** Closes #9 (Async Retrieval with FAISS)

## [0.8.1] - 2026-01-09

### Added
- **GigaChat Scope Auto-Detection**: `GigaChatValidator.validate()` now accepts optional `scope` parameter
  - If `scope` is not provided, validator automatically tries all variants (PERS → B2B → CORP)
  - Stops immediately on errors other than scope mismatch (401, 429, 500, timeout)
  - Returns `detected_scope` in `ValidationResult.details`
  - Progress callback `on_scope_attempt` for real-time UI feedback
  - Metrics in `details`: `auto_detection_used`, `attempts_count`, `total_time_ms`, `attempted_scopes`, `stopped_reason`

### Changed
- `GigaChatValidator.validate()`: `scope` parameter is now `Optional[str]` (was `str`)
  - Backward compatible: explicit `scope` still works (skips auto-detection)
  - Auto-detection only runs when `scope` is `None`
- `GigaChatProvider.validate_api_key()`: Added handling for 429 rate limit at OAuth2 endpoint

### Documentation
- Updated README.md with auto-detection examples and limitations
- Updated `examples/validation_demo.py` with auto-detection examples
- Added `examples/platform_saas_integration.py` demonstrating full integration with progress tracking
- Added performance note for auto-detection (up to 3 OAuth2 requests, 3-6 seconds)

### Notes
- Auto-detection makes up to 3 OAuth2 requests (one per scope), which can take 3-6 seconds
- For faster validation, specify the scope explicitly if known
- Progress callback is only called during auto-detection (not when scope is explicitly provided)

## [0.8.0] - 2026-01-17

### Added
- **API Key Validators** module (`orchestrator.validators`)
  - `GigaChatValidator` for validating GigaChat API keys with known scope
  - `YandexGPTValidator` for validating YandexGPT IAM tokens and folder_id
  - Structured error types (`ValidationResult`, `ErrorCode`)
  - Support for `verify_ssl` parameter (GigaChat)
  - Request ID extraction for YandexGPT errors
  - Comprehensive test coverage (80%+)

### Changed
- Made `GigaChatProvider.get_access_token()` public (was `_get_access_token`)
  - Enables validators to reuse OAuth2 authentication logic
  - Maintains backward compatibility (internal method still works)

### Documentation
- Added "API Key Validation" section to README
- Added `examples/validation_demo.py` with usage examples
- Added Google-style docstrings to all validators

### Notes
- Scope auto-detection for GigaChat is planned for v0.8.1
- Validators are designed for Platform SaaS use cases (key validation during onboarding)

## [0.7.6] - 2026-01-10

### Added
- **Usage tracking callbacks** for billing and analytics integration ([#7](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/issues/7))
  - Python callback support via `usage_callback` parameter
  - HTTP POST callback support via `callback_url` parameter
  - Optional context fields: `tenant_id`, `platform_key_id`
  - Comprehensive usage data: tokens, cost, latency, success status
  - Fail-silent behavior: callback errors don't disrupt requests
  - Full streaming support (`route()` and `route_stream()`)
  - Complete fallback support (callback invoked for each provider attempt)

### Examples
```python
# Python callback
async def track_usage(data: UsageData) -> None:
    print(f"Cost: {data.cost} RUB, Tokens: {data.total_tokens}")

router = Router(usage_callback=track_usage)

# HTTP POST callback (for Platform SaaS)
router = Router(
    callback_url="https://api.example.com/usage",
    tenant_id="tenant-123",
    platform_key_id="key-456",
)
```

### Breaking Changes
None - fully backward compatible.

## [0.7.5] - 2025-12-28

### Added
- `Router.update_providers()` method for zero-downtime provider updates
  - Optional `preserve_metrics` parameter to preserve metrics for matching provider names
  - Validation for empty list and duplicate provider names
  - Model change detection with WARNING log
  - Atomic swap with round-robin index reset
- 8 comprehensive tests covering all edge cases

### Fixed
- Race condition in `route()` and `route_stream()`: safe metrics access with on-the-fly creation
- Active requests now complete successfully during provider updates

### Changed
- Improved metrics reliability during provider updates

**Use Case:** Platform SaaS (Managed→BYOK migrations, API key rotation)

**Closes:** #5

## [0.7.4] - 2024-12-24

### 🐛 Bug Fixes

#### Event Loop Cleanup in Telegram Bot Pattern ([#4](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/issues/4))

**Problem:**
- ~50% failure rate in production Telegram bots using `asyncio.to_thread()` pattern
- "Event loop is closed" errors due to httpx cleanup executing AFTER `loop.close()`
- Race condition in httpx `AsyncClient` cleanup tasks

**Root Cause:**
When using the pattern `async context → asyncio.to_thread() → asyncio.run() → Router`:
1. `asyncio.run()` creates new event loop
2. httpx `AsyncClient` schedules cleanup tasks (`aclose()`)
3. `loop.close()` executes before cleanup tasks run
4. httpx attempts cleanup on closed loop → RuntimeError

**Solution:**
Enhanced event loop cleanup sequence in three components:

1. **LangChain wrapper** (`src/orchestrator/langchain.py`):
   - Replaced `asyncio.run()` with manual event loop management
   - Added cleanup steps: `asyncio.sleep(0)` → `shutdown_asyncgens()` → `shutdown_default_executor()`
   - Ensures all pending tasks complete before `loop.close()`

2. **YandexGPT provider** (`src/orchestrator/providers/yandexgpt.py`):
   - Replaced singleton `httpx.AsyncClient` with context managers
   - Each request creates new client: `async with httpx.AsyncClient() as client:`
   - Cleanup executes automatically when exiting context manager

3. **GigaChat provider** (`src/orchestrator/providers/gigachat.py`):
   - Replaced singleton `httpx.AsyncClient` with context managers
   - Preserved OAuth2 token management and 401 retry logic
   - Enhanced streaming with nested context managers

**Impact:**
- ✅ 100% success rate in Telegram bot pattern (was ~50%)
- ✅ Thread-safe cleanup in high-load scenarios
- ✅ Fixes production issues in bots processing hundreds of requests/hour

**Technical Details:**
```python
# Enhanced cleanup sequence (langchain.py)
loop = asyncio.new_event_loop()
try:
    result = loop.run_until_complete(coro)
    loop.run_until_complete(asyncio.sleep(0))  # Process pending callbacks
    loop.run_until_complete(loop.shutdown_asyncgens())  # Close async generators
    if hasattr(loop, 'shutdown_default_executor'):
        loop.run_until_complete(loop.shutdown_default_executor())  # Close thread pool
    return result
finally:
    loop.close()
```

**Overhead:**
- YandexGPT/GigaChat: +150ms per request (TCP+TLS handshake)
- Acceptable for 2-5s LLM inference times
- Trade-off: Reliability > Marginal performance cost

**Testing:**
- Added integration test: `tests/integration/test_telegram_bot_issue.py`
- Added manual test script: `examples/telegram_bot_pattern.py`
- Verified with production Telegram bot workloads

**Credits:**
- Issue reported by: [@MikhailMalorod](https://github.com/MikhailMalorod)
- Root cause analysis: Python asyncio + httpx internals investigation
- Fix validated with: pytest + manual Telegram bot testing

---

## [0.7.3] - 2025-12-24

### Fixed

- **CRITICAL**: Fixed "Event loop is closed" error on repeated requests in async contexts (#2)
  - Root cause: `loop.close()` left closed event loop in thread-local storage
  - ThreadPoolExecutor reuses threads → closed loop reused on every even request → 50% success rate
  - Solution: Replace manual event loop management with `asyncio.run()` for automatic cleanup
  - Affected methods: `MultiLLMOrchestrator._call()` and `._generate()`
  - Multiple sequential requests now work correctly in Telegram bots, FastAPI, and other async applications

### Technical Details

- **Pattern**: Every even request (2nd, 4th, 6th, ...) failed with `"Event loop is closed"`
- **ThreadPoolExecutor behavior**: Reuses threads for efficiency, which reused closed event loops
- **asyncio.run() advantage**: Automatically calls `asyncio.set_event_loop(None)` to clean thread-local state
- **Production impact**: Telegram bot had ~50% success rate (every second user message failed)

### Migration

- **No action required** for users — upgrade to v0.7.3 and the issue is resolved automatically
- If using **v0.7.0**: Upgrade to v0.7.3 to fix both Issue #1 (asyncio.run in running loop) and #2
- If using **v0.7.2**: Upgrade to v0.7.3 immediately (critical regression fix)

### Testing

- Added regression tests: `test_multiple_calls_from_async_context()`, `test_multiple_generate_calls_from_async_context()`, `test_rapid_fire_requests()`
- Verified locally that multiple sequential and concurrent calls from async contexts no longer produce `"Event loop is closed"`

### Regression

- v0.7.2 introduced event loop closure bug affecting production Telegram bots
- Second and subsequent requests in thread pool could fail with `RuntimeError: Event loop is closed`
- Fixed by using `asyncio.run()` which creates an isolated event loop per call with proper cleanup

## [0.7.2] - 2025-12-23

### Fixed

- **Prometheus metrics endpoint charset**: Fixed charset conflict in `/metrics` endpoint response headers
  - Content-Type now correctly includes `charset=utf-8` without conflicts
  - Added unit test to verify charset handling
  
- **Provider prefix matching**: Fixed "Unknown provider" warnings for provider variants
  - `get_price_per_1k()` now supports longest-prefix matching (e.g., "mock-1" → "mock")
  - Added helper function `_find_provider_prefix()` for consistent matching logic
  - Edge cases handled: "gigachat-pro-custom" → "gigachat-pro" (longest match)
  - False positives prevented: "mockery" doesn't match "mock" (requires "-" separator)
  
- **tiktoken Windows compatibility**: Updated to version 0.12.0 for pre-built Windows wheels
  - Resolves compilation issues on Windows systems
  - Previous version (^0.5.2) required compilation from source

### Testing

- Added unit test for Prometheus endpoint charset verification
- Added comprehensive tests for provider prefix matching edge cases
- All existing tests continue to pass (203+ tests)

### Notes

- Backward compatible with v0.7.0 (no breaking changes)
- Test coverage maintained at ≥81%
- Includes fix for Issue #1 related to `RuntimeError: asyncio.run() cannot be called from a running event loop` when calling sync APIs from async contexts

## [0.7.0] - 2024-12-22

### Added

- **Token-aware Metrics**: Track token usage and costs for LLM requests
  - Prompt token tracking via `total_prompt_tokens` field in `ProviderMetrics`
  - Completion token tracking via `total_completion_tokens` field
  - Total tokens computed property (`total_tokens = prompt + completion`)
  - Cost estimation in RUB for GigaChat and YandexGPT providers
  - `tiktoken` integration for accurate GPT-like token counting
  - Fallback to word-based estimation (`word_count * 1.3`) when tiktoken fails
  - Automatic token counting in both `route()` and `route_stream()` methods

- **Prometheus Integration**: Export metrics for monitoring systems
  - HTTP endpoint `/metrics` for Prometheus scraping (standard format)
  - `Router.start_metrics_server(port)` method to start HTTP server
  - `Router.stop_metrics_server()` method for graceful shutdown
  - Background task updates metrics every 1 second
  - Metrics exported:
    - `llm_requests_total` — Request counters by provider and status
    - `llm_request_latency_seconds` — Latency histogram with 8 buckets
    - `llm_tokens_total` — Token counters by provider and type (prompt/completion)
    - `llm_cost_total` — Total cost in RUB by provider
    - `llm_provider_health` — Health status gauge (1=healthy, 0.5=degraded, 0=unhealthy)

- **New Modules**:
  - `orchestrator.tokenization` — Token counting utilities with tiktoken + fallback
  - `orchestrator.pricing` — Cost estimation logic with pricing table
  - `orchestrator.prometheus_exporter` — Prometheus HTTP server implementation

- **Enhanced Structured Logging**: Token and cost info in request logs
  - Log fields now include: `prompt_tokens`, `completion_tokens`, `total_tokens`, `cost_rub`
  - Cost rounded to 2 decimals in logs for readability

### Changed

- `ProviderMetrics.record_success()` signature extended (backward compatible):
  - New optional parameters: `prompt_tokens=0`, `completion_tokens=0`, `cost=0.0`
  - Old code without token parameters still works (defaults to 0)
- `Router._log_request_event()` signature extended with token/cost fields (backward compatible)

### Documentation

- New comprehensive guide: `docs/observability.md`
  - Token tracking and cost estimation documentation
  - Prometheus integration setup guide
  - Example Prometheus queries for monitoring
  - Grafana dashboard recommendations
  - Troubleshooting section
- README updated with "Prometheus Integration" section
- Examples: `examples/prometheus_demo.py` — working Prometheus demo

### Dependencies

- Added: `prometheus-client` ^0.19.0
- Added: `tiktoken` ^0.12.0 (updated from ^0.5.2 in v0.7.1 for Windows compatibility)
- Added: `aiohttp` ^3.9.1

### Notes

- Backward compatible with v0.6.0 (no breaking changes)
- Test coverage: 81% (decreased from 92% due to HTTP server testing complexity)
- All 202 tests passing

## [0.6.0] - 2024-XX-XX

### Added

- **Provider Metrics System**: Comprehensive metrics tracking for each provider
  - Automatic tracking of request counts (total, successful, failed)
  - Latency metrics: average latency and rolling average latency (last 100 requests)
  - Error rate tracking with configurable time windows
  - Health status determination (`healthy`, `degraded`, `unhealthy`)
  - Accessible via `router.get_metrics()` method

- **Best-Available Routing Strategy**: Intelligent provider selection based on metrics
  - Selects providers based on health status (healthy > degraded > unhealthy)
  - Optimizes for lowest latency within the same health tier
  - Real-time adaptation to changing provider performance
  - Automatic deprioritization of underperforming providers

- **Health Status Classification**: Automatic provider health assessment
  - `healthy`: Low error rate (<30%), normal latency patterns
  - `degraded`: Moderate error rate (30-60%) or latency degradation
  - `unhealthy`: High error rate (>60%)
  - Optimistic default for new providers (insufficient data)

- **Structured Logging**: Enhanced logging with structured request events
  - `llm_request_completed` events (info level) for successful requests
  - `llm_request_failed` events (warning level) for failed requests
  - Includes: provider name, model, latency_ms, streaming flag, success status, error_type

- **Battle-Tested Metrics Script**: Real-world testing script (`test_metrics_real.py`)
  - Tests basic metrics collection with successful requests
  - Tests metrics with error fallback and health degradation
  - Tests metrics with streaming requests
  - Formatted metrics output with rich/ASCII tables

### Changed

- Router now automatically initializes metrics for each provider when added
- Metrics are updated after each request (both `route()` and `route_stream()`)
- Health status calculation requires minimum 5 requests for accurate assessment
- Latency degradation detection requires minimum 20 requests

### Documentation

- Updated `README.md` with metrics and best-available strategy examples
- Updated `docs/architecture.md` with comprehensive metrics system documentation
- Added health status logic explanation
- Documented structured logging format

## [0.5.0] - 2024-XX-XX

### Added

- Initial release with core routing functionality
- Support for GigaChat, YandexGPT, Ollama, and Mock providers
- Multiple routing strategies: round-robin, random, first-available
- Automatic fallback mechanism
- Streaming support
- LangChain integration
