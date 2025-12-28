# 🚀 Implementation Plan: v0.7.0 — Token-aware Metrics & Prometheus Integration

> **Target Release**: December 22, 2025  
> **Current Status**: ✅ **IMPLEMENTATION COMPLETE**  
> **Overall Progress**: 100% (10/10 major tasks completed) ✅  
> **Completion Date**: December 12, 2025

---

## 📊 Implementation Progress

| Phase | Task | Status | Priority |
|-------|------|--------|----------|
| **Phase 1: Core Infrastructure** | | **3/3 completed** | |
| 1.1 | Create `tokenization.py` module | ✅ Completed | 🔴 Critical |
| 1.2 | Create `pricing.py` module | ✅ Completed | 🔴 Critical |
| 1.3 | Extend `ProviderMetrics` class | ✅ Completed | 🔴 Critical |
| **Phase 2: Router Integration** | | **2/2 completed** | |
| 2.1 | Integrate tokenization in `Router.route()` | ✅ Completed | 🔴 Critical |
| 2.2 | Integrate tokenization in `Router.route_stream()` | ✅ Completed | 🔴 Critical |
| **Phase 3: Prometheus** | | **2/2 completed** | |
| 3.1 | Create `prometheus_exporter.py` module | ✅ Completed | 🟡 High |
| 3.2 | Add metrics server lifecycle to Router | ✅ Completed | 🟡 High |
| **Phase 4: Testing** | | **1/1 completed** | |
| 4.1 | Unit tests (tokenization, pricing, metrics) | ✅ Completed | 🔴 Critical |
| **Phase 5: Documentation** | | **2/2 completed** | |
| 5.1 | Update docs (README, observability.md, CHANGELOG) | ✅ Completed | 🟡 High |
| 5.2 | Create `examples/prometheus_demo.py` | ✅ Completed | 🟡 High |

---

## 📦 Modules Overview

### New Modules (3)
1. **`src/orchestrator/tokenization.py`** — Token counting with tiktoken + fallback
2. **`src/orchestrator/pricing.py`** — Cost estimation for providers
3. **`src/orchestrator/prometheus_exporter.py`** — Prometheus metrics HTTP server

### Modified Modules (2)
4. **`src/orchestrator/metrics.py`** — Extend `ProviderMetrics` with token/cost fields
5. **`src/orchestrator/router.py`** — Integrate tokenization + metrics server lifecycle

### New Test Files (3)
6. **`tests/test_tokenization.py`** — Unit tests for token counting
7. **`tests/test_pricing.py`** — Unit tests for cost estimation
8. **`tests/test_prometheus.py`** — Unit tests for Prometheus format (optional: integration tests)

### New Documentation (2)
9. **`docs/observability.md`** — Comprehensive guide on metrics and Prometheus
10. **`examples/prometheus_demo.py`** — Working example

---

## 🔧 Phase 1: Core Infrastructure

### Task 1.1: Create `tokenization.py` Module ⬜️

**File**: `src/orchestrator/tokenization.py`

**Purpose**: Centralized token counting with tiktoken + fallback logic

**Implementation Details**:

```python
"""Token counting utilities for LLM requests."""

import logging
from typing import Optional

logger = logging.getLogger("orchestrator.tokenization")

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Count tokens using tiktoken with fallback to word-based estimation.
    
    Args:
        text: Input text to tokenize
        model: Model name for tiktoken encoding (default: gpt-3.5-turbo)
        
    Returns:
        Token count (exact via tiktoken or estimated via word count * 1.3)
        
    Example:
        >>> count_tokens("Hello, world!")
        4  # Exact count via tiktoken
        
        >>> count_tokens("Привет, мир!", model="unsupported")
        3  # Fallback: 2 words * 1.3 ≈ 3 tokens
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback to word-based estimation
        logger.warning(
            f"tiktoken failed for model '{model}': {e}. "
            f"Using fallback estimation (word_count * 1.3)"
        )
        return estimate_tokens_fallback(text)

def estimate_tokens_fallback(text: str) -> int:
    """Fallback token estimation using word count * 1.3.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count (word_count * 1.3, rounded to int)
        
    Note:
        This is a rough approximation. For English text, 1 token ≈ 0.75 words,
        so 1 word ≈ 1.3 tokens. For other languages, accuracy may vary.
    """
    word_count = len(text.split())
    return int(word_count * 1.3)
```

**Key Design Decisions**:
- ✅ Single entry point: `count_tokens()`
- ✅ Automatic fallback on tiktoken errors
- ✅ Warning logging for transparency
- ✅ Type hints + docstrings

**Testing Requirements**:
- Test `count_tokens()` with various inputs
- Test fallback when tiktoken raises exception
- Test `estimate_tokens_fallback()` accuracy

---

### Task 1.2: Create `pricing.py` Module ⬜️

**File**: `src/orchestrator/pricing.py`

**Purpose**: Cost estimation based on provider + model + token count

**Implementation Details**:

```python
"""Cost estimation for LLM providers."""

import logging
from typing import Optional

logger = logging.getLogger("orchestrator.pricing")

# Pricing in RUB per 1000 tokens (unified, no prompt/completion split)
PRICING = {
    "gigachat": {
        "GigaChat": 1.00,
        "GigaChat-Pro": 2.00,
        "GigaChat-Plus": 1.50,
        "default": 1.50,
    },
    "yandexgpt": {
        "yandexgpt/latest": 1.50,
        "yandexgpt-lite/latest": 0.75,
        "default": 1.50,
    },
    "ollama": {
        "default": 0.0,
    },
    "mock": {
        "default": 0.0,
    },
}

def calculate_cost(
    provider_name: str,
    model: Optional[str],
    total_tokens: int
) -> float:
    """Calculate cost in RUB for LLM request.
    
    Args:
        provider_name: Provider name (e.g., "gigachat", "yandexgpt")
        model: Model name (e.g., "GigaChat-Pro", "yandexgpt/latest")
        total_tokens: Total token count (prompt + completion)
        
    Returns:
        Cost in rubles (float, unrounded)
        
    Example:
        >>> calculate_cost("gigachat", "GigaChat-Pro", 1500)
        3.0  # 1500 tokens * 2.00 RUB / 1000 = 3.0 RUB
        
        >>> calculate_cost("ollama", "llama2", 1000)
        0.0  # Ollama is free
    """
    # Normalize provider name to lowercase
    provider_key = provider_name.lower()
    
    # Get provider pricing config
    provider_pricing = PRICING.get(provider_key)
    if not provider_pricing:
        logger.warning(
            f"Unknown provider '{provider_name}', assuming zero cost"
        )
        return 0.0
    
    # Get model-specific price or default
    price_per_1k = provider_pricing.get(model or "default")
    if price_per_1k is None:
        price_per_1k = provider_pricing.get("default", 0.0)
        logger.warning(
            f"Unknown model '{model}' for provider '{provider_name}', "
            f"using default price: {price_per_1k} RUB/1K tokens"
        )
    
    # Calculate cost
    cost = (total_tokens / 1000.0) * price_per_1k
    return cost

def get_price_per_1k(provider_name: str, model: Optional[str]) -> float:
    """Get price per 1000 tokens for a provider/model.
    
    Args:
        provider_name: Provider name
        model: Model name
        
    Returns:
        Price per 1000 tokens in RUB
    """
    provider_key = provider_name.lower()
    provider_pricing = PRICING.get(provider_key, {})
    return provider_pricing.get(model or "default", provider_pricing.get("default", 0.0))
```

**Key Design Decisions**:
- ✅ Centralized pricing table (easy to update)
- ✅ Case-insensitive provider lookup
- ✅ Default fallback for unknown models
- ✅ Warning logs for unknown providers/models
- ✅ Unrounded float for precision (round at display time)

**Testing Requirements**:
- Test all provider/model combinations from PRICING table
- Test unknown provider → 0.0 cost
- Test unknown model → default price
- Test cost calculation accuracy

---

### Task 1.3: Extend `ProviderMetrics` Class ⬜️

**File**: `src/orchestrator/metrics.py` (MODIFY)

**Purpose**: Add token tracking and cost tracking to existing metrics

**Implementation Details**:

```python
# Add to ProviderMetrics.__init__():
def __init__(self) -> None:
    # ... existing fields ...
    
    # NEW: Token tracking (v0.7.0)
    self.total_prompt_tokens: int = 0
    self.total_completion_tokens: int = 0
    self.total_cost: float = 0.0

# Add computed property:
@property
def total_tokens(self) -> int:
    """Total tokens processed (prompt + completion).
    
    Returns:
        Sum of prompt and completion tokens
    """
    return self.total_prompt_tokens + self.total_completion_tokens

# Modify record_success signature (backward compatible with defaults):
def record_success(
    self,
    latency_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost: float = 0.0,
) -> None:
    """Record a successful request with latency, tokens, and cost.
    
    Args:
        latency_ms: Request latency in milliseconds
        prompt_tokens: Number of tokens in prompt (default: 0)
        completion_tokens: Number of tokens in completion (default: 0)
        cost: Request cost in RUB (default: 0.0)
    """
    # Existing logic
    self.total_requests += 1
    self.successful_requests += 1
    self.total_latency_ms += latency_ms
    self._latency_window.append(latency_ms)
    
    # NEW: Update token and cost tracking
    self.total_prompt_tokens += prompt_tokens
    self.total_completion_tokens += completion_tokens
    self.total_cost += cost
```

**Key Design Decisions**:
- ✅ Backward compatible (default values for new params)
- ✅ `total_tokens` as computed property (no redundant storage)
- ✅ No breaking changes to existing code
- ✅ `record_error()` unchanged (no tokens for failed requests)

**Testing Requirements**:
- Test backward compatibility (old code still works)
- Test new fields initialized to 0
- Test `record_success()` with token/cost params
- Test `total_tokens` computed property

---

## 🔌 Phase 2: Router Integration

### Task 2.1: Integrate Tokenization in `Router.route()` ⬜️

**File**: `src/orchestrator/router.py` (MODIFY)

**Location**: After line 239 (`result = await provider.generate(prompt, params)`)

**Implementation Details**:

```python
# Add imports at top:
from .tokenization import count_tokens
from .pricing import calculate_cost

# In route() method, after successful generation:
try:
    # ... existing code ...
    result = await provider.generate(prompt, params)
    
    # Calculate latency (existing)
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    # NEW: Count tokens
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(result)
    total_tokens = prompt_tokens + completion_tokens
    
    # NEW: Calculate cost
    cost = calculate_cost(
        provider_name=provider.config.name,
        model=provider.config.model,
        total_tokens=total_tokens
    )
    
    # Update metrics (modified signature)
    metrics = self.metrics[provider.config.name]
    metrics.record_success(
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=cost
    )
    
    # Log success event (add token info to structured log)
    self._log_request_event(
        provider_name=provider.config.name,
        model=provider.config.model,
        latency_ms=latency_ms,
        streaming=False,
        success=True,
        # NEW fields:
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=cost
    )
    
    # ... existing return ...
```

**Key Design Decisions**:
- ✅ Tokenization happens AFTER provider returns result
- ✅ No changes to BaseProvider interface
- ✅ Structured logging includes token/cost info
- ✅ Backward compatible (existing code without tokens still works)

**Testing Requirements**:
- Test `route()` still works without breaking changes
- Test token counting is accurate
- Test cost calculation is correct
- Test metrics are updated properly

---

### Task 2.2: Integrate Tokenization in `Router.route_stream()` ⬜️

**File**: `src/orchestrator/router.py` (MODIFY)

**Location**: After streaming completes (line 556-567)

**Implementation Details**:

```python
# In route_stream() method:
async def route_stream(...) -> AsyncIterator[str]:
    # ... existing selection logic ...
    
    for i in range(len(self.providers)):
        # ... existing provider selection ...
        
        start_time = time.perf_counter()
        first_chunk_sent = False
        
        # NEW: Accumulate chunks for token counting
        accumulated_chunks: list[str] = []
        
        try:
            async for chunk in provider.generate_stream(prompt, params):
                if not first_chunk_sent:
                    first_chunk_sent = True
                
                # NEW: Accumulate chunks
                accumulated_chunks.append(chunk)
                
                # Yield chunk to caller
                yield chunk
            
            # Streaming completed successfully
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # NEW: Reconstruct full response for tokenization
            full_response = "".join(accumulated_chunks)
            
            # NEW: Count tokens
            prompt_tokens = count_tokens(prompt)
            completion_tokens = count_tokens(full_response)
            total_tokens = prompt_tokens + completion_tokens
            
            # NEW: Calculate cost
            cost = calculate_cost(
                provider_name=provider.config.name,
                model=provider.config.model,
                total_tokens=total_tokens
            )
            
            # Update metrics
            metrics = self.metrics[provider.config.name]
            metrics.record_success(
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost
            )
            
            # Log success event (add token info)
            self._log_request_event(
                provider_name=provider.config.name,
                model=provider.config.model,
                latency_ms=latency_ms,
                streaming=True,
                success=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost
            )
            
            return
            
        except Exception as stream_error:
            # ... existing error handling ...
```

**Key Design Decisions**:
- ✅ Accumulate chunks in memory (acceptable for LLM responses)
- ✅ Tokenization happens AFTER streaming completes
- ✅ Document memory overhead in docstring
- ✅ No breaking changes to streaming interface

**Testing Requirements**:
- Test streaming still works correctly
- Test token counting for streamed responses
- Test accumulated chunks match original response

---

### Task 2.3: Update `_log_request_event()` Signature ⬜️

**File**: `src/orchestrator/router.py` (MODIFY)

**Location**: Lines 141-176

**Implementation Details**:

```python
def _log_request_event(
    self,
    provider_name: str,
    model: str | None,
    latency_ms: float,
    streaming: bool,
    success: bool,
    error_type: str | None = None,
    # NEW: Token and cost fields (optional, backward compatible)
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    cost: float | None = None,
) -> None:
    """Log a request event with structured fields.
    
    ... existing docstring ...
    
    Args (NEW):
        prompt_tokens: Number of prompt tokens (optional)
        completion_tokens: Number of completion tokens (optional)
        total_tokens: Total tokens (optional)
        cost: Request cost in RUB (optional)
    """
    extra = {
        "provider": provider_name,
        "model": model,
        "latency_ms": latency_ms,
        "streaming": streaming,
        "success": success,
    }
    
    # Add error info
    if error_type:
        extra["error_type"] = error_type
    
    # NEW: Add token and cost info (if available)
    if prompt_tokens is not None:
        extra["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        extra["completion_tokens"] = completion_tokens
    if total_tokens is not None:
        extra["total_tokens"] = total_tokens
    if cost is not None:
        extra["cost_rub"] = round(cost, 2)  # Round to 2 decimals for logs
    
    if success:
        self.logger.info("llm_request_completed", extra=extra)
    else:
        self.logger.warning("llm_request_failed", extra=extra)
```

**Key Design Decisions**:
- ✅ Optional parameters (backward compatible)
- ✅ Cost rounded to 2 decimals in logs (for readability)
- ✅ Only include token/cost if provided (no None in logs)

---

## 📊 Phase 3: Prometheus Integration

### Task 3.1: Create `prometheus_exporter.py` Module ⬜️

**File**: `src/orchestrator/prometheus_exporter.py`

**Purpose**: HTTP server for Prometheus metrics export

**Implementation Details**:

```python
"""Prometheus metrics exporter for Multi-LLM Orchestrator."""

import asyncio
import logging
from typing import Dict

from aiohttp import web
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    REGISTRY,
    CollectorRegistry,
)

logger = logging.getLogger("orchestrator.prometheus")

# Metric definitions
REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total number of LLM requests",
    ["provider", "status"],
)

REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "Latency of LLM requests in seconds",
    ["provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")],
)

TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total tokens processed",
    ["provider", "type"],  # type = "prompt" or "completion"
)

COST_TOTAL = Counter(
    "llm_cost_total",
    "Total cost in rubles",
    ["provider"],
)

PROVIDER_HEALTH = Gauge(
    "llm_provider_health",
    "Provider health status (1=healthy, 0.5=degraded, 0=unhealthy)",
    ["provider"],
)


class PrometheusExporter:
    """Prometheus metrics exporter with HTTP server.
    
    Provides /metrics endpoint for Prometheus scraping.
    
    Example:
        >>> exporter = PrometheusExporter(port=9090)
        >>> await exporter.start()
        >>> # Metrics available at http://localhost:9090/metrics
        >>> await exporter.stop()
    """
    
    def __init__(self, port: int = 9090) -> None:
        """Initialize Prometheus exporter.
        
        Args:
            port: HTTP server port (default: 9090)
        """
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/metrics", self._metrics_handler)
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self._metrics_dict: Dict[str, any] = {}
        
    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """Handle /metrics endpoint."""
        # Generate Prometheus format
        metrics_output = generate_latest(REGISTRY)
        return web.Response(
            body=metrics_output,
            content_type="text/plain; version=0.0.4; charset=utf-8"
        )
    
    async def start(self) -> None:
        """Start HTTP server (non-blocking).
        
        Raises:
            OSError: If port is already in use
        """
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()
            logger.info(f"Prometheus metrics server started on port {self.port}")
        except OSError as e:
            if "Address already in use" in str(e):
                raise OSError(
                    f"Port {self.port} is already in use. "
                    "Choose a different port or stop the conflicting service."
                ) from e
            raise
    
    async def stop(self) -> None:
        """Stop HTTP server gracefully."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Prometheus metrics server stopped")
    
    def update_metrics(self, metrics_dict: Dict[str, any]) -> None:
        """Update Prometheus metrics from ProviderMetrics.
        
        Args:
            metrics_dict: Dictionary of provider_name -> ProviderMetrics
        """
        for provider_name, provider_metrics in metrics_dict.items():
            # Update counters
            REQUESTS_TOTAL.labels(
                provider=provider_name, status="success"
            )._value.set(provider_metrics.successful_requests)
            
            REQUESTS_TOTAL.labels(
                provider=provider_name, status="failure"
            )._value.set(provider_metrics.failed_requests)
            
            TOKENS_TOTAL.labels(
                provider=provider_name, type="prompt"
            )._value.set(provider_metrics.total_prompt_tokens)
            
            TOKENS_TOTAL.labels(
                provider=provider_name, type="completion"
            )._value.set(provider_metrics.total_completion_tokens)
            
            COST_TOTAL.labels(
                provider=provider_name
            )._value.set(provider_metrics.total_cost)
            
            # Update gauge (health status)
            health_value = {
                "healthy": 1.0,
                "degraded": 0.5,
                "unhealthy": 0.0,
            }.get(provider_metrics.health_status, 0.0)
            
            PROVIDER_HEALTH.labels(provider=provider_name).set(health_value)
            
            # Update histogram (latency)
            # Note: We need to manually update histogram buckets
            # This is a simplified approach - in production, you'd track individual observations
            avg_latency_seconds = provider_metrics.avg_latency_ms / 1000.0
            REQUEST_LATENCY.labels(provider=provider_name).observe(avg_latency_seconds)
```

**Key Design Decisions**:
- ✅ aiohttp for lightweight async HTTP server
- ✅ prometheus_client for standard Prometheus format
- ✅ Non-blocking startup (asyncio.create_task in Router)
- ✅ Graceful shutdown
- ✅ Error handling for port conflicts

**Testing Requirements**:
- Test HTTP server starts/stops correctly
- Test /metrics endpoint returns valid Prometheus format
- Test metrics are updated correctly
- Test port conflict raises clear error

---

### Task 3.2: Add Metrics Server Lifecycle to Router ⬜️

**File**: `src/orchestrator/router.py` (MODIFY)

**Implementation Details**:

```python
# Add import at top:
from .prometheus_exporter import PrometheusExporter

# Add to Router.__init__():
def __init__(self, strategy: str = "round-robin") -> None:
    # ... existing initialization ...
    
    # NEW: Prometheus exporter (not started by default)
    self._prometheus_exporter: PrometheusExporter | None = None
    self._metrics_update_task: asyncio.Task | None = None

# Add new methods:
async def start_metrics_server(self, port: int = 9090) -> None:
    """Start Prometheus metrics HTTP server.
    
    Args:
        port: HTTP server port (default: 9090)
        
    Raises:
        OSError: If port is already in use
        RuntimeError: If metrics server is already running
        
    Example:
        >>> router = Router()
        >>> await router.start_metrics_server(port=9090)
        >>> # Metrics available at http://localhost:9090/metrics
    """
    if self._prometheus_exporter is not None:
        raise RuntimeError("Metrics server is already running")
    
    self._prometheus_exporter = PrometheusExporter(port=port)
    await self._prometheus_exporter.start()
    
    # Start background task to update metrics periodically
    self._metrics_update_task = asyncio.create_task(
        self._update_metrics_loop()
    )
    
    self.logger.info(f"Metrics server started on http://0.0.0.0:{port}/metrics")

async def stop_metrics_server(self) -> None:
    """Stop Prometheus metrics HTTP server gracefully.
    
    Example:
        >>> await router.stop_metrics_server()
    """
    if self._metrics_update_task:
        self._metrics_update_task.cancel()
        try:
            await self._metrics_update_task
        except asyncio.CancelledError:
            pass
    
    if self._prometheus_exporter:
        await self._prometheus_exporter.stop()
        self._prometheus_exporter = None
    
    self.logger.info("Metrics server stopped")

async def _update_metrics_loop(self) -> None:
    """Background task to update Prometheus metrics every 1 second."""
    while True:
        try:
            if self._prometheus_exporter:
                self._prometheus_exporter.update_metrics(self.metrics)
            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
            await asyncio.sleep(1.0)
```

**Key Design Decisions**:
- ✅ Explicit start/stop (not automatic)
- ✅ Background task updates metrics every 1 second
- ✅ Graceful cancellation on stop
- ✅ Clear error messages

**Testing Requirements**:
- Test start_metrics_server() starts successfully
- Test stop_metrics_server() stops gracefully
- Test error if port is in use
- Test error if starting twice

---

## 🧪 Phase 4: Testing

### Task 4.1: Unit Tests for Tokenization ⬜️

**File**: `tests/test_tokenization.py` (NEW)

**Test Coverage**:
```python
"""Unit tests for tokenization module."""

import pytest
from unittest.mock import patch

from orchestrator.tokenization import count_tokens, estimate_tokens_fallback


class TestCountTokens:
    def test_count_tokens_basic(self) -> None:
        """Test basic token counting."""
        text = "Hello, world!"
        tokens = count_tokens(text)
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_count_tokens_empty_string(self) -> None:
        """Test token counting for empty string."""
        assert count_tokens("") == 0
    
    def test_count_tokens_long_text(self) -> None:
        """Test token counting for long text."""
        text = "This is a longer sentence with multiple words. " * 100
        tokens = count_tokens(text)
        assert tokens > 100  # Should have many tokens
    
    @patch("orchestrator.tokenization.tiktoken.encoding_for_model")
    def test_count_tokens_fallback_on_error(self, mock_encoding) -> None:
        """Test fallback to word count when tiktoken fails."""
        mock_encoding.side_effect = Exception("tiktoken error")
        
        text = "Hello world test"  # 3 words
        tokens = count_tokens(text)
        
        # Should use fallback: 3 words * 1.3 = 3.9 ≈ 3
        assert tokens == int(3 * 1.3)


class TestEstimateTokensFallback:
    def test_estimate_tokens_basic(self) -> None:
        """Test fallback estimation."""
        text = "Hello world"  # 2 words
        tokens = estimate_tokens_fallback(text)
        assert tokens == int(2 * 1.3)  # 2.6 ≈ 2
    
    def test_estimate_tokens_empty(self) -> None:
        """Test fallback for empty string."""
        assert estimate_tokens_fallback("") == 0
    
    def test_estimate_tokens_single_word(self) -> None:
        """Test fallback for single word."""
        tokens = estimate_tokens_fallback("Hello")
        assert tokens == int(1 * 1.3)  # 1.3 ≈ 1
```

**Expected Coverage**: 95%+

---

### Task 4.2: Unit Tests for Pricing ⬜️

**File**: `tests/test_pricing.py` (NEW)

**Test Coverage**:
```python
"""Unit tests for pricing module."""

import pytest
from orchestrator.pricing import calculate_cost, get_price_per_1k, PRICING


class TestCalculateCost:
    def test_calculate_cost_gigachat(self) -> None:
        """Test cost calculation for GigaChat."""
        cost = calculate_cost("gigachat", "GigaChat", 1000)
        assert cost == 1.00
        
        cost = calculate_cost("gigachat", "GigaChat-Pro", 1000)
        assert cost == 2.00
        
        cost = calculate_cost("gigachat", "GigaChat-Plus", 1000)
        assert cost == 1.50
    
    def test_calculate_cost_yandexgpt(self) -> None:
        """Test cost calculation for YandexGPT."""
        cost = calculate_cost("yandexgpt", "yandexgpt/latest", 1000)
        assert cost == 1.50
        
        cost = calculate_cost("yandexgpt", "yandexgpt-lite/latest", 1000)
        assert cost == 0.75
    
    def test_calculate_cost_free_providers(self) -> None:
        """Test cost calculation for free providers."""
        assert calculate_cost("ollama", "llama2", 1000) == 0.0
        assert calculate_cost("mock", "mock-normal", 1000) == 0.0
    
    def test_calculate_cost_unknown_provider(self) -> None:
        """Test cost calculation for unknown provider."""
        cost = calculate_cost("unknown-provider", "unknown-model", 1000)
        assert cost == 0.0
    
    def test_calculate_cost_unknown_model_uses_default(self) -> None:
        """Test that unknown model uses default price."""
        cost = calculate_cost("gigachat", "GigaChat-Ultra-New", 1000)
        assert cost == 1.50  # default for gigachat
    
    def test_calculate_cost_fractional_tokens(self) -> None:
        """Test cost calculation with fractional token counts."""
        cost = calculate_cost("gigachat", "GigaChat-Pro", 1500)
        assert cost == pytest.approx(3.0)  # 1500 * 2.00 / 1000 = 3.0
```

**Expected Coverage**: 100%

---

### Task 4.3: Unit Tests for Extended Metrics ⬜️

**File**: `tests/test_metrics.py` (MODIFY)

**New Test Cases**:
```python
class TestProviderMetricsTokenTracking:
    """Test token tracking in ProviderMetrics."""
    
    def test_initial_token_values(self) -> None:
        """Test that token fields initialize to 0."""
        metrics = ProviderMetrics()
        assert metrics.total_prompt_tokens == 0
        assert metrics.total_completion_tokens == 0
        assert metrics.total_tokens == 0  # computed property
        assert metrics.total_cost == 0.0
    
    def test_record_success_with_tokens(self) -> None:
        """Test record_success with token parameters."""
        metrics = ProviderMetrics()
        metrics.record_success(
            latency_ms=100.0,
            prompt_tokens=50,
            completion_tokens=30,
            cost=0.16
        )
        
        assert metrics.total_prompt_tokens == 50
        assert metrics.total_completion_tokens == 30
        assert metrics.total_tokens == 80
        assert metrics.total_cost == pytest.approx(0.16)
    
    def test_record_success_backward_compatible(self) -> None:
        """Test that old code without tokens still works."""
        metrics = ProviderMetrics()
        metrics.record_success(100.0)  # Old signature
        
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.total_prompt_tokens == 0  # Defaults to 0
        assert metrics.total_cost == 0.0
    
    def test_multiple_requests_accumulate_tokens(self) -> None:
        """Test that multiple requests accumulate tokens correctly."""
        metrics = ProviderMetrics()
        
        metrics.record_success(100.0, prompt_tokens=10, completion_tokens=20, cost=0.05)
        metrics.record_success(150.0, prompt_tokens=15, completion_tokens=25, cost=0.08)
        
        assert metrics.total_prompt_tokens == 25
        assert metrics.total_completion_tokens == 45
        assert metrics.total_tokens == 70
        assert metrics.total_cost == pytest.approx(0.13)
```

**Expected Coverage**: 90%+ (maintaining high coverage)

---

### Task 4.4: Unit Tests for Prometheus Exporter ⬜️

**File**: `tests/test_prometheus.py` (NEW)

**Test Coverage** (OPTIONAL — nice-to-have):
```python
"""Unit tests for Prometheus exporter."""

import pytest
from orchestrator.prometheus_exporter import PrometheusExporter
from orchestrator.metrics import ProviderMetrics


class TestPrometheusExporter:
    @pytest.mark.asyncio
    async def test_exporter_starts_and_stops(self) -> None:
        """Test that exporter starts and stops correctly."""
        exporter = PrometheusExporter(port=9091)
        
        await exporter.start()
        # Server should be running
        
        await exporter.stop()
        # Server should be stopped
    
    @pytest.mark.asyncio
    async def test_exporter_port_conflict(self) -> None:
        """Test that port conflict raises clear error."""
        exporter1 = PrometheusExporter(port=9092)
        await exporter1.start()
        
        exporter2 = PrometheusExporter(port=9092)
        with pytest.raises(OSError, match="already in use"):
            await exporter2.start()
        
        await exporter1.stop()
    
    def test_update_metrics(self) -> None:
        """Test that metrics are updated correctly."""
        exporter = PrometheusExporter()
        
        # Create mock metrics
        metrics = ProviderMetrics()
        metrics.record_success(100.0, prompt_tokens=10, completion_tokens=20, cost=0.05)
        
        # Update Prometheus metrics
        exporter.update_metrics({"test-provider": metrics})
        
        # Verify metrics were updated (check internal state)
        # This is a simplified test - full implementation would verify Prometheus format
```

**Expected Coverage**: 70%+ (optional, complex HTTP testing)

---

## 📚 Phase 5: Documentation

### Task 5.1: Update Documentation ⬜️

**Files to Update**:

#### 5.1.1: `README.md` (ADD new section)

**Location**: After "Streaming Support" section

```markdown
## Prometheus Integration

Monitor your LLM infrastructure with Prometheus metrics:

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig

async def main():
    router = Router(strategy="best-available")
    
    # Add providers
    config = ProviderConfig(
        name="gigachat",
        api_key="your_api_key",
        model="GigaChat-Pro"
    )
    router.add_provider(GigaChatProvider(config))
    
    # Start Prometheus metrics server
    await router.start_metrics_server(port=9090)
    
    # Make requests
    response = await router.route("Hello!")
    
    # Access metrics programmatically
    metrics = router.get_metrics()
    for provider_name, provider_metrics in metrics.items():
        print(f"{provider_name}:")
        print(f"  Total requests: {provider_metrics.total_requests}")
        print(f"  Total tokens: {provider_metrics.total_tokens}")
        print(f"  Total cost: {provider_metrics.total_cost:.2f} RUB")
    
    # Metrics available at http://localhost:9090/metrics
    # Stop server when done
    await router.stop_metrics_server()

asyncio.run(main())
```

**Available Metrics**:
- `llm_requests_total` — Total requests (success/failure)
- `llm_request_latency_seconds` — Request latency histogram
- `llm_tokens_total` — Total tokens processed (prompt/completion)
- `llm_cost_total` — Total cost in RUB
- `llm_provider_health` — Provider health status (1=healthy, 0.5=degraded, 0=unhealthy)

See [docs/observability.md](docs/observability.md) for detailed guide.
```

---

#### 5.1.2: `docs/observability.md` (CREATE NEW)

**Purpose**: Comprehensive guide on observability, metrics, and Prometheus

**Structure**:
```markdown
# Observability Guide

## Overview
Multi-LLM Orchestrator provides comprehensive observability through:
- Provider-level metrics (latency, success rates, health)
- Token tracking and cost estimation
- Prometheus integration for monitoring

## Token Tracking

### How It Works
- Uses `tiktoken` for GPT-like models
- Fallback to word-based estimation (word_count * 1.3)
- Tracks prompt tokens, completion tokens, and total tokens

### Cost Estimation
Pricing (RUB per 1000 tokens):
- **GigaChat**: 1.00 (standard), 2.00 (Pro), 1.50 (Plus)
- **YandexGPT**: 1.50 (latest), 0.75 (lite)
- **Ollama/Mock**: Free

### Accessing Metrics Programmatically
```python
metrics = router.get_metrics()
for provider_name, provider_metrics in metrics.items():
    print(f"Provider: {provider_name}")
    print(f"  Total tokens: {provider_metrics.total_tokens}")
    print(f"  Total cost: {provider_metrics.total_cost:.2f} RUB")
```

## Prometheus Integration

### Starting Metrics Server
```python
await router.start_metrics_server(port=9090)
# Metrics: http://localhost:9090/metrics
```

### Prometheus Configuration
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'llm-orchestrator'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

### Example Queries
```promql
# Request rate (requests/sec)
rate(llm_requests_total[5m])

# Success rate (%)
sum(rate(llm_requests_total{status="success"}[5m])) /
sum(rate(llm_requests_total[5m])) * 100

# Average latency (seconds)
rate(llm_request_latency_seconds_sum[5m]) /
rate(llm_request_latency_seconds_count[5m])

# Total cost per provider (RUB)
llm_cost_total

# Unhealthy providers
llm_provider_health < 1.0
```

### Grafana Dashboard
Create panels with these queries for visualization.

## Troubleshooting

### Port Already in Use
```python
# Error: OSError: Port 9090 is already in use
# Solution: Use different port
await router.start_metrics_server(port=9091)
```

### High Token Counts (Fallback Warning)
If you see warnings about tiktoken fallback, the token counts are estimates (not exact).
Install tiktoken: `pip install tiktoken`

### Metrics Not Updating
Metrics update every 1 second in background task. Wait 1-2 seconds after requests.
```

---

#### 5.1.3: `CHANGELOG.md` (UPDATE)

**Add v0.7.0 Section**:
```markdown
## [0.7.0] - 2024-12-22

### Added
- **Token-aware Metrics**:
  - Track prompt tokens, completion tokens, and total tokens per provider
  - Cost estimation for GigaChat and YandexGPT (RUB per 1000 tokens)
  - `tiktoken` integration for accurate token counting
  - Fallback to word-based estimation (word_count * 1.3)
  - New fields in `ProviderMetrics`: `total_prompt_tokens`, `total_completion_tokens`, `total_cost`
  
- **Prometheus Integration**:
  - HTTP endpoint (`/metrics`) for Prometheus scraping
  - Metrics: `llm_requests_total`, `llm_request_latency_seconds`, `llm_tokens_total`, `llm_cost_total`, `llm_provider_health`
  - `Router.start_metrics_server(port)` and `Router.stop_metrics_server()` methods
  - Background task updates metrics every 1 second
  
- **New Modules**:
  - `orchestrator.tokenization` — Token counting utilities
  - `orchestrator.pricing` — Cost estimation logic
  - `orchestrator.prometheus_exporter` — Prometheus HTTP server

- **Documentation**:
  - New guide: `docs/observability.md`
  - README section: "Prometheus Integration"
  - Example: `examples/prometheus_demo.py`

### Changed
- `ProviderMetrics.record_success()` signature extended (backward compatible)
- Structured logging now includes token and cost info

### Dependencies
- Added: `prometheus-client` ^0.19.0
- Added: `tiktoken` ^0.5.2
- Added: `aiohttp` ^3.9.1

### Notes
- Backward compatible with v0.6.0
- Target test coverage: 85%+ (decreased from 92% due to HTTP mocking complexity)
```

---

### Task 5.2: Create Prometheus Demo Example ⬜️

**File**: `examples/prometheus_demo.py` (NEW)

```python
"""Prometheus Integration Demo

This example demonstrates:
1. Starting Prometheus metrics server
2. Making LLM requests with multiple providers
3. Accessing metrics programmatically
4. Viewing metrics via HTTP endpoint

Run:
    python examples/prometheus_demo.py

Then visit: http://localhost:9090/metrics
"""

import asyncio
import time
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider


async def main() -> None:
    print("🚀 Multi-LLM Orchestrator — Prometheus Demo\n")
    
    # Initialize router
    router = Router(strategy="best-available")
    
    # Add multiple providers
    for i in range(3):
        config = ProviderConfig(name=f"provider-{i+1}", model="mock-normal")
        router.add_provider(MockProvider(config))
    
    print("✅ Added 3 providers\n")
    
    # Start Prometheus metrics server
    print("📊 Starting Prometheus metrics server...")
    await router.start_metrics_server(port=9090)
    print("✅ Metrics server running at: http://localhost:9090/metrics\n")
    
    # Make some requests
    print("📤 Making 10 requests...")
    for i in range(10):
        prompt = f"Request {i+1}: Hello, world!"
        response = await router.route(prompt)
        print(f"  [{i+1}/10] Response length: {len(response)} chars")
    
    print("\n✅ All requests completed\n")
    
    # Wait for metrics to update
    await asyncio.sleep(2)
    
    # Access metrics programmatically
    print("📈 Provider Metrics:")
    print("-" * 60)
    
    metrics = router.get_metrics()
    for provider_name, provider_metrics in metrics.items():
        print(f"\n{provider_name}:")
        print(f"  Total Requests:       {provider_metrics.total_requests}")
        print(f"  Successful:           {provider_metrics.successful_requests}")
        print(f"  Failed:               {provider_metrics.failed_requests}")
        print(f"  Success Rate:         {provider_metrics.success_rate:.1%}")
        print(f"  Avg Latency:          {provider_metrics.avg_latency_ms:.1f} ms")
        print(f"  Health Status:        {provider_metrics.health_status}")
        print(f"  Total Tokens:         {provider_metrics.total_tokens}")
        print(f"  Total Cost:           {provider_metrics.total_cost:.2f} RUB")
    
    print("\n" + "-" * 60)
    print("\n📊 Prometheus metrics available at: http://localhost:9090/metrics")
    print("   Try these queries in Prometheus/Grafana:")
    print("     - llm_requests_total")
    print("     - llm_tokens_total")
    print("     - llm_cost_total")
    print("     - llm_provider_health")
    
    print("\n⏸️  Press Ctrl+C to stop...\n")
    
    # Keep server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping metrics server...")
        await router.stop_metrics_server()
        print("✅ Metrics server stopped")
        print("\n👋 Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🎯 Implementation Checklist

### Pre-Implementation
- ✅ All questions answered
- ✅ Plan reviewed and approved
- ⬜️ Dependencies added to `pyproject.toml`

### Phase 1: Core Infrastructure (Est: 2-3 days)
- ⬜️ Task 1.1: `tokenization.py` module
- ⬜️ Task 1.2: `pricing.py` module
- ⬜️ Task 1.3: Extend `ProviderMetrics`

### Phase 2: Router Integration (Est: 1-2 days)
- ⬜️ Task 2.1: Integrate in `Router.route()`
- ⬜️ Task 2.2: Integrate in `Router.route_stream()`
- ⬜️ Task 2.3: Update `_log_request_event()`

### Phase 3: Prometheus (Est: 1-2 days)
- ⬜️ Task 3.1: `prometheus_exporter.py` module
- ⬜️ Task 3.2: Metrics server lifecycle in Router

### Phase 4: Testing (Est: 1-2 days)
- ⬜️ Task 4.1: Unit tests for tokenization
- ⬜️ Task 4.2: Unit tests for pricing
- ⬜️ Task 4.3: Unit tests for extended metrics
- ⬜️ Task 4.4: Unit tests for Prometheus (optional)

### Phase 5: Documentation (Est: 1 day)
- ⬜️ Task 5.1.1: Update README
- ⬜️ Task 5.1.2: Create `docs/observability.md`
- ⬜️ Task 5.1.3: Update CHANGELOG
- ⬜️ Task 5.2: Create `examples/prometheus_demo.py`

### Final Steps
- ⬜️ Run full test suite (`pytest --cov`)
- ⬜️ Verify coverage >= 85%
- ⬜️ Run mypy strict mode (no errors)
- ⬜️ Run ruff linter (no errors)
- ⬜️ Manual testing with real providers
- ⬜️ Update version in `pyproject.toml` to 0.7.0
- ⬜️ Create git tag `v0.7.0`
- ⬜️ Publish to PyPI

---

## 🔑 Key Design Principles

1. **Backward Compatibility**: All changes must work with existing v0.6.0 code
2. **Minimal Invasiveness**: No breaking changes to BaseProvider or public APIs
3. **Graceful Degradation**: Token counting failures fall back to estimation
4. **Clear Error Messages**: All errors should guide users to solutions
5. **Comprehensive Logging**: All critical operations are logged
6. **Type Safety**: Full type hints + mypy strict mode compliance
7. **Test Coverage**: Maintain high coverage (target: 85%+)
8. **Documentation-First**: Every feature has clear examples

---

## 📝 Notes for Implementation

### Dependencies to Add
```toml
[tool.poetry.dependencies]
prometheus-client = "^0.19.0"
tiktoken = "^0.5.2"
aiohttp = "^3.9.1"
```

### Potential Challenges
1. **Streaming Token Accumulation**: Memory overhead for long responses
   - Mitigation: Document memory usage, acceptable for typical LLM responses
   
2. **HTTP Server Port Conflicts**: Multiple Router instances
   - Mitigation: Clear error messages, suggest different ports
   
3. **tiktoken Installation**: Optional C extensions
   - Mitigation: Fallback mechanism, clear warnings

4. **Prometheus Histogram Complexity**: Tracking individual latency observations
   - Mitigation: Simplified approach for v0.7.0, improve in v0.8.0

### Out of Scope for v0.7.0
- ❌ Provider-specific tokenizers (native APIs)
- ❌ SentencePiece for Ollama
- ❌ Push to Prometheus Pushgateway
- ❌ File-based metrics export
- ❌ Detailed latency percentiles (p50, p95, p99)
- ❌ Per-request metrics history

---

## 🚀 Ready to Implement!

This plan provides a clear roadmap for implementing v0.7.0. Each task is:
- **Modular**: Can be implemented independently
- **Testable**: Clear testing requirements
- **Documented**: Inline examples and docstrings
- **Elegant**: Follows existing code style and patterns

**Next Step**: Begin Phase 1, Task 1.1 (Create `tokenization.py`)

---

*Last Updated: December 12, 2025*  
*Plan Status: ✅ Complete — Ready for Implementation*

