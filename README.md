# Multi-LLM Orchestrator

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PyPI](https://img.shields.io/pypi/v/multi-llm-orchestrator.svg)
![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)
![Tests](https://img.shields.io/badge/tests-241%20passed-success.svg)

## Architecture

![Multi-LLM Orchestrator Architecture](docs/images/architecture-v0.7.0.png)

Multi-LLM Orchestrator provides automatic failover between GigaChat, YandexGPT, and Ollama with streaming support.


A unified interface for orchestrating multiple Large Language Model providers with intelligent routing and fallback mechanisms.

## Overview

The Multi-LLM Orchestrator provides a seamless way to integrate and manage multiple LLM providers through a single, consistent interface. It supports intelligent routing strategies, automatic fallbacks, provider-level metrics tracking, and provider-specific optimizations. Currently focused on Russian LLM providers (GigaChat, YandexGPT) with a flexible architecture that supports any LLM provider implementation.

## Features

- **Multiple LLM Providers**: Unified interface for GigaChat, YandexGPT, Ollama, and custom providers
- **Intelligent Routing**: Multiple routing strategies including round-robin, random, first-available, and best-available (health + latency aware)
- **Automatic Fallback**: Seamless failover when providers fail
- **Provider-level Metrics**: Track latency, success/failure rates, and health status for each provider
- **Smart Routing Strategy**: `best-available` strategy selects the healthiest provider with lowest latency based on real-time metrics
- **Streaming Support**: Incremental text generation with streaming responses
- **LangChain Integration**: Optional compatibility layer for LangChain chains and prompts
- **Async Retrieval (v0.9.0+)**: GIL-free FAISS vectorstore wrapper with **4ms p99 latency** for concurrent queries

## Async Retrieval (v0.9.0+)

**AsyncFAISSRetriever** provides async wrapper for LangChain FAISS vectorstore with GIL mitigation, enabling efficient concurrent document retrieval in shared asyncio event loops (e.g., Telegram bot pools, FastAPI applications).

### Performance Benchmarks

Real-world performance on 1000-document FAISS index (384-dim embeddings):

| Metric | Result | Notes |
|--------|--------|-------|
| **10 concurrent queries (p99)** | **4.01ms** | Primary acceptance criteria: <5s ✅ |
| **100 concurrent queries (p99)** | 13.40ms | Stress test: <10s ✅ |
| **Throughput** | 4,859 qps | 46x above minimum threshold |
| **Memory overhead** | +0.98MB | 1000 queries, no leaks detected |

### Quick Start

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
for doc, score in results:
    print(f"Score: {score:.4f}, Content: {doc.page_content}")

# MMR search (diversity-aware)
docs = await retriever.max_marginal_relevance_search(
    "query", k=5, lambda_mult=0.5
)

# Cleanup
await retriever.close()
```

### Installation

```bash
pip install multi-llm-orchestrator[retrieval]
# Includes: faiss-cpu, langchain-core, langchain-community
```

### Features

- ✅ **GIL mitigation** via `asyncio.to_thread()` - prevents blocking in shared event loops
- ✅ **4ms p99 latency** for 10 concurrent queries (1247x better than 5s threshold)
- ✅ **Thread pool management** - custom executor support, context manager, automatic cleanup
- ✅ **LangChain compatibility** - seamless integration via `BaseRetriever` interface
- ✅ **Filter support** - dict and callable metadata filters
- ✅ **MMR search** - diversity-aware retrieval with configurable lambda_mult

### LangChain Integration

```python
# Use as LangChain BaseRetriever
lc_retriever = retriever.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)

# Async retrieval (recommended)
docs = await lc_retriever.ainvoke("query")

# Use in LangChain chains
from langchain.chains import RetrievalQA
chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=lc_retriever
)
```

📖 **Complete documentation**: [docs/retrieval.md](docs/retrieval.md)  
🎯 **Examples**: [examples/async_faiss_demo.py](examples/async_faiss_demo.py)

## Quickstart

Get started with Multi-LLM Orchestrator in minutes:

### Using MockProvider (Testing)

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider

async def main():
    # Initialize router with round-robin strategy
    router = Router(strategy="round-robin")
    
    # Add providers
    for i in range(3):
        config = ProviderConfig(name=f"provider-{i+1}", model="mock-normal")
        router.add_provider(MockProvider(config))
    
    # Make a request
    response = await router.route("What is Python?")
    print(response)
    # Output: Mock response to: What is Python?

if __name__ == "__main__":
    asyncio.run(main())
```

### Using GigaChatProvider (Production)

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, GigaChatProvider

async def main():
    # Create GigaChat provider
    config = ProviderConfig(
        name="gigachat",
        api_key="your_authorization_key_here",  # OAuth2 authorization key
        model="GigaChat",  # or "GigaChat-Pro", "GigaChat-Plus"
        scope="GIGACHAT_API_PERS"  # or "GIGACHAT_API_CORP" for corporate
    )
    provider = GigaChatProvider(config)
    
    # Use with router
    router = Router(strategy="round-robin")
    router.add_provider(provider)
    
    # Generate response
    response = await router.route("What is Python?")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### Disabling SSL Verification (for self-signed certificates)

If you encounter SSL certificate errors with GigaChat (Russian CA certificates), you can disable verification:

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig

async def main():
    router = Router(strategy="round-robin")
    
    # WARNING: Disabling SSL verification is insecure
    # Use only in development or with trusted networks
    config = ProviderConfig(
        name="gigachat",
        api_key="your_authorization_key_here",
        scope="GIGACHAT_API_PERS",
        verify_ssl=False  # Disable SSL verification
    )
    
    router.add_provider(GigaChatProvider(config))
    
    response = await router.route("Hello!")
    print(response)

asyncio.run(main())
```

**⚠️ Security Warning:** Disabling SSL verification makes your application vulnerable to man-in-the-middle attacks. Use this option only in development or when working with known self-signed certificates.

### Using YandexGPTProvider (Production)

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, YandexGPTProvider

async def main():
    # Create YandexGPT provider
    config = ProviderConfig(
        name="yandexgpt",
        api_key="your_iam_token_here",  # IAM token (valid for 12 hours)
        folder_id="your_folder_id_here",  # Yandex Cloud folder ID
        model="yandexgpt/latest"  # or "yandexgpt-lite/latest"
    )
    provider = YandexGPTProvider(config)
    
    # Use with router
    router = Router(strategy="round-robin")
    router.add_provider(provider)
    
    # Generate response
    response = await router.route("What is Python?")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### Local Models with Ollama

Run open-source LLMs locally without API keys:

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import OllamaProvider, ProviderConfig

async def main():
    router = Router(strategy="first-available")

    ollama_config = ProviderConfig(
        name="ollama",
        model="llama3",  # or "mistral", "phi", etc.
        base_url="http://localhost:11434",  # optional; defaults to localhost
    )
    router.add_provider(OllamaProvider(ollama_config))

    response = await router.route("Why is the sky blue?")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

**Requirements:** Install Ollama from <https://ollama.ai> and pull a model (e.g., `ollama pull llama3`).

The MockProvider simulates LLM behavior without requiring API credentials, while GigaChatProvider and YandexGPTProvider provide full integration with their respective APIs.

## Installation

**Requirements:**

- Python 3.11+
- Poetry (recommended) or pip

### Using Poetry

```bash
# Clone the repository
git clone https://github.com/MikhailMalorod/Multi-LLM-Orchestrator.git
cd Multi-LLM-Orchestrator

# Install dependencies
poetry install
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/MikhailMalorod/Multi-LLM-Orchestrator.git
cd Multi-LLM-Orchestrator

# Install in development mode
pip install -e .
```

## Architecture

The Multi-LLM Orchestrator follows a modular architecture with clear separation of concerns:

```
┌──────────────────────────────────────────────┐
│              User Application                │
└─────────────────┬────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │     Router     │ ◄── Strategy: round-robin/random/first-available/best-available
         └────────┬───────┘
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│Provider 1│ │Provider 2│ │Provider 3│
│(Base)    │ │(Base)    │ │(Base)    │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     ▼            ▼            ▼
   (API)        (API)        (API)
```

### Components

- **Router** (`src/orchestrator/router.py`): Manages provider selection based on routing strategy and handles automatic fallback when providers fail.

- **BaseProvider** (`src/orchestrator/providers/base.py`): Abstract base class defining the interface that all provider implementations must follow. Includes configuration models (`ProviderConfig`, `GenerationParams`) and exception hierarchy.

- **MockProvider** (`src/orchestrator/providers/mock.py`): Test implementation that simulates LLM behavior without making actual API calls. Supports various simulation modes for testing different scenarios.

- **Config** (`src/orchestrator/config.py`): Future component for loading configuration from environment variables. Currently used for planned real provider integrations (GigaChat, YandexGPT).

## Routing Strategies

The Router supports four routing strategies, each suitable for different use cases:

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **round-robin** | Cycles through providers in a fixed order | Equal load distribution (recommended for production) |
| **random** | Selects a random provider from available providers | Simple random selection for load balancing |
| **first-available** | Selects the first healthy provider based on health checks | High availability scenarios with automatic unhealthy provider skipping |
| **best-available** | Selects the healthiest provider with lowest latency based on real-time metrics | Production environments requiring optimal performance and reliability |

The strategy is selected when initializing the Router:

```python
router = Router(strategy="round-robin")  # or "random", "first-available", or "best-available"
```

### Best-Available Strategy

The `best-available` strategy uses provider health status and latency metrics to intelligently route requests:

- **Health Status**: Providers are categorized as `healthy`, `degraded`, or `unhealthy` based on error rates and latency patterns
- **Latency Optimization**: Among providers with the same health status, selects the one with the lowest rolling average latency
- **Automatic Adaptation**: Metrics are updated in real-time, so routing decisions adapt as provider performance changes

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, GigaChatProvider, YandexGPTProvider

async def main():
    # Initialize router with best-available strategy
    router = Router(strategy="best-available")
    
    # Add multiple providers
    router.add_provider(GigaChatProvider(ProviderConfig(
        name="gigachat", api_key="key1", model="GigaChat"
    )))
    router.add_provider(YandexGPTProvider(ProviderConfig(
        name="yandexgpt", api_key="key2", folder_id="folder1", model="yandexgpt/latest"
    )))
    
    # Router will automatically select the healthiest and fastest provider
    response = await router.route("What is Python?")
    print(response)

asyncio.run(main())
```

The Router tracks performance metrics for each provider (latency, success rate, error rate) and uses this data to make intelligent routing decisions. Providers with high error rates or degraded latency are automatically deprioritized.

## Zero-downtime Provider Updates

Update providers without recreating Router instance:

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, YandexGPTProvider, ProviderConfig

async def main():
    router = Router(strategy="best-available")
    
    # Add initial providers
    router.add_provider(GigaChatProvider(ProviderConfig(
        name="gigachat", api_key="key1", model="GigaChat"
    )))
    
    # ... later, update providers without downtime ...
    
    # Reset metrics (default)
    await router.update_providers([
        GigaChatProvider(ProviderConfig(name="gigachat", api_key="new_key", model="GigaChat-Pro")),
        YandexGPTProvider(ProviderConfig(name="yandexgpt", api_key="key2", folder_id="folder", model="yandexgpt/latest"))
    ])
    
    # Preserve metrics for matching provider names
    await router.update_providers([new_gigachat], preserve_metrics=True)

asyncio.run(main())
```

**Features:**
- Zero-downtime: Active requests complete on old providers
- Optional metrics preservation
- Validation (empty list, duplicate names)
- Model change detection

**Use Cases:**
- API key rotation
- Managed→BYOK migrations
- Dynamic configuration updates

## Run the Demo

See the routing strategies and fallback mechanisms in action:

```bash
python examples/routing_demo.py
```

**No API keys required** — uses MockProvider for demonstration.

The demo showcases:
- All four routing strategies (round-robin, random, first-available, best-available)
- Automatic fallback mechanism when providers fail
- Error handling when all providers are unavailable

See [routing_demo.py](examples/routing_demo.py) for the complete interactive demonstration.

## MockProvider Modes

MockProvider simulates various LLM behaviors for testing without requiring API credentials:

- **`mock-normal`** — Returns successful responses with a small delay
- **`mock-timeout`** — Simulates timeout errors
- **`mock-unhealthy`** — Health check returns `False` (useful for testing `first-available` strategy)
- **`mock-ratelimit`** — Simulates rate limit errors
- **`mock-auth-error`** — Simulates authentication failures

See [mock.py](src/orchestrator/providers/mock.py) for all available modes and detailed documentation.

## Roadmap

See our [GitHub Issues](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/issues) for planned features and roadmap updates.

### Current Status

- ✅ Core architecture with Router and BaseProvider
- ✅ MockProvider for testing
- ✅ GigaChatProvider with OAuth2 authentication
- ✅ Four routing strategies (round-robin, random, first-available, best-available)
- ✅ Provider-level metrics tracking (latency, success/failure, health status)
- ✅ Automatic fallback mechanism
- ✅ Example demonstrations

### Supported Providers

- ✅ **MockProvider** — For testing and development
- ✅ **GigaChatProvider** — Full integration with GigaChat (Sber) API
  - OAuth2 authentication with automatic token refresh
  - Support for all generation parameters
  - Comprehensive error handling
- ✅ **YandexGPTProvider** — Full integration with YandexGPT (Yandex Cloud) API
  - IAM token authentication (user-managed, 12-hour validity)
  - Support for temperature and maxTokens parameters
  - Support for yandexgpt/latest and yandexgpt-lite/latest models
  - Comprehensive error handling
- ✅ **OllamaProvider** — Local models (Llama 3, Mistral, Phi) via Ollama API

### Planned Providers

- [ ] Additional open-source providers (TBD)

## LangChain Integration

> **Note:** Requires optional dependency. Install with:
> ```bash
> pip install multi-llm-orchestrator[langchain]
> ```

Use Multi-LLM Orchestrator providers with LangChain chains, prompts, and other LangChain components:

```python
from langchain_core.prompts import ChatPromptTemplate
from orchestrator.langchain import MultiLLMOrchestrator
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig

# Create router with providers
router = Router(strategy="round-robin")
config = ProviderConfig(
    name="gigachat",
    api_key="your_api_key",
    model="GigaChat"
)
router.add_provider(GigaChatProvider(config))

# Use as LangChain LLM
llm = MultiLLMOrchestrator(router=router)

# Work with LangChain chains
prompt = ChatPromptTemplate.from_template("Tell me about {topic}")
chain = prompt | llm
response = chain.invoke({"topic": "Python"})
```

The `MultiLLMOrchestrator` class implements LangChain's `BaseLLM` interface, supporting both synchronous and asynchronous calls. All routing strategies and fallback mechanisms work seamlessly with LangChain.

## Prometheus Integration

Monitor your LLM infrastructure with Prometheus metrics and token-aware cost tracking:

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

**Token Tracking & Cost Estimation**:
- **GigaChat**: ₽1.00 (base), ₽2.00 (Pro), ₽1.50 (Plus) per 1K tokens
- **YandexGPT**: ₽1.50 (latest), ₽0.75 (lite) per 1K tokens
- **Ollama/Mock**: Free

See [docs/observability.md](docs/observability.md) for detailed guide.

## Usage Tracking

Track LLM usage for billing and analytics using callbacks. Supports both Python callbacks for in-process tracking and HTTP POST callbacks for remote billing APIs.

### Python Callback

Use a Python async function to track usage data:

```python
import asyncio
from orchestrator import Router, UsageData
from orchestrator.providers import ProviderConfig, MockProvider

async def track_usage(data: UsageData) -> None:
    """Send usage data to billing API."""
    print(f"Provider: {data.provider_name}")
    print(f"Model: {data.model}")
    print(f"Tokens: {data.total_tokens} (prompt: {data.prompt_tokens}, completion: {data.completion_tokens})")
    print(f"Cost: {data.cost:.2f} RUB")
    print(f"Latency: {data.latency_ms:.2f}ms")
    print(f"Success: {data.success}")
    # Send to your billing API here

async def main():
    router = Router(strategy="round-robin", usage_callback=track_usage)
    config = ProviderConfig(name="provider1", model="mock-normal")
    router.add_provider(MockProvider(config))
    
    response = await router.route("What is Python?")
    print(response)

asyncio.run(main())
```

### HTTP POST Callback

For remote billing APIs in multi-tenant deployments:

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider

async def main():
    router = Router(
        strategy="round-robin",
        callback_url="https://api.example.com/usage",
        tenant_id="tenant-123",
        platform_key_id="key-456",
    )
    config = ProviderConfig(name="provider1", model="mock-normal")
    router.add_provider(MockProvider(config))
    
    response = await router.route("What is Python?")
    print(response)

asyncio.run(main())
```

**Payload Format** (JSON, snake_case):

```json
{
  "provider": "gigachat",
  "model": "GigaChat-Pro",
  "prompt_tokens": 42,
  "completion_tokens": 128,
  "total_tokens": 170,
  "cost": 3.40,
  "latency_ms": 1234.56,
  "success": true,
  "streaming": false,
  "timestamp": "2026-01-12T15:30:00.000000Z",
  "tenant_id": "tenant-123",
  "platform_key_id": "key-456"
}
```

**Features:**
- ✅ Automatic tracking for all requests (success and failure)
- ✅ Full fallback support (callback invoked for each provider attempt)
- ✅ Streaming support (`route()` and `route_stream()`)
- ✅ Fail-silent behavior (callback errors don't disrupt requests)
- ✅ Comprehensive usage data (tokens, cost, latency, success status)

**Note:** You cannot specify both `usage_callback` and `callback_url` at the same time. Choose one based on your use case.

## Streaming Support

Multi-LLM Orchestrator now supports streaming responses, allowing you to receive text chunks incrementally as they are generated. This is especially useful for real-time applications and improved user experience.

### Basic Streaming with Router

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider

async def main():
    router = Router(strategy="round-robin")
    config = ProviderConfig(name="mock", model="mock-normal")
    router.add_provider(MockProvider(config))
    
    # Stream response chunk by chunk
    async for chunk in router.route_stream("What is Python?"):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

### Streaming with LangChain

```python
from orchestrator.langchain import MultiLLMOrchestrator
from orchestrator import Router
from orchestrator.providers import MockProvider, ProviderConfig

router = Router(strategy="round-robin")
router.add_provider(MockProvider(ProviderConfig(name="mock", model="mock-normal")))

llm = MultiLLMOrchestrator(router=router)

# Async streaming
async for chunk in llm._astream("What is Python?"):
    print(chunk, end="", flush=True)

# Sync streaming
for chunk in llm._stream("What is Python?"):
    print(chunk, end="", flush=True)
```

### Streaming Features

- **Incremental responses**: Receive text chunks as they are generated
- **Fallback support**: Automatic provider fallback works before the first chunk is yielded
- **Provider support**: Currently supported in MockProvider and GigaChatProvider
- **LangChain integration**: Full support for both sync and async streaming in LangChain

### Streaming Examples

See [streaming_demo.py](examples/streaming_demo.py) and [langchain_streaming_demo.py](examples/langchain_streaming_demo.py) for complete examples.

## API Key Validation

Multi-LLM-Orchestrator provides validators for checking API keys before usage. This is especially useful for Platform SaaS applications where users need to validate their API keys during onboarding.

### Quick Start

```python
from orchestrator.validators import GigaChatValidator, YandexGPTValidator, ErrorCode

# GigaChat (with known scope)
validator = GigaChatValidator(verify_ssl=False)  # For Russian CA
result = await validator.validate(
    api_key="YOUR_API_KEY",
    scope="GIGACHAT_API_PERS"
)

if result.valid:
    print(f"✅ Valid! Scope: {result.details['scope']}")
elif result.error_code == ErrorCode.SCOPE_MISMATCH:
    print(f"❌ Scope mismatch: {result.message}")
elif result.error_code == ErrorCode.RATE_LIMIT_EXCEEDED:
    print(f"⏳ Rate limited, retry after {result.retry_after}s")
else:
    print(f"❌ Error: {result.error_code.value} - {result.message}")

# YandexGPT
validator = YandexGPTValidator()
result = await validator.validate(
    api_key="YOUR_IAM_TOKEN",
    folder_id="YOUR_FOLDER_ID"
)

if result.valid:
    print("✅ Valid!")
elif result.error_code == ErrorCode.PERMISSION_DENIED:
    print(f"❌ No access to folder_id: {result.details['folder_id']}")
    print(f"Request ID: {result.details.get('request_id')}")
```

### GigaChat Scope Auto-Detection (v0.8.1+)

GigaChatValidator can automatically detect the scope (PERS/B2B/CORP) if not provided:

```python
validator = GigaChatValidator()

# Auto-detect scope (tries PERS → B2B → CORP)
result = await validator.validate("YOUR_API_KEY")

if result.valid:
    detected_scope = result.details.get("detected_scope")
    print(f"✅ Valid! Auto-detected scope: {detected_scope}")
    print(f"   Attempts: {result.details.get('attempts_count')}")
    print(f"   Time: {result.details.get('total_time_ms')}ms")
else:
    print(f"❌ Error: {result.error_code.value}")

# Or specify scope explicitly (faster, skips auto-detection)
result = await validator.validate("YOUR_API_KEY", scope="GIGACHAT_API_B2B")
```

**Performance Note**: Auto-detection makes up to 3 OAuth2 requests (one per scope), which can take 3-6 seconds. For faster validation, specify the scope explicitly if known.

#### Progress Tracking

For better UX during auto-detection, use the `on_scope_attempt` callback:

```python
def show_progress(scope: str, current: int, total: int):
    print(f"Checking {scope} ({current}/{total})...")

result = await validator.validate(
    "YOUR_API_KEY",
    on_scope_attempt=show_progress
)
```

#### Auto-Detection Limitations

**1. Expired Keys**
If the API key is expired (401), auto-detection stops immediately without testing other scopes.

**Reason**: 401 indicates authentication failure unrelated to scope. Testing other scopes would waste time and API quota.

**Example**:
```python
# Expired key
result = await validator.validate("EXPIRED_KEY")
# Result: INVALID_API_KEY (stopped after first 401, did not try B2B/CORP)
```

**2. Rate Limits**
If rate limit (429) is hit during auto-detection, the process stops immediately.

**Reason**: Rate limits apply across all scopes. Continuing would hit the same limit.

**Workaround**: Wait for `retry_after` seconds (returned in `ValidationResult.retry_after`) and retry.

**3. Response Time**
Auto-detection makes **up to 3 OAuth2 requests** (one per scope), which can take 3-6 seconds.

**Optimization**: If you know the scope, pass it explicitly to skip auto-detection:
```python
# Fast (1 request, ~1-2 seconds)
result = await validator.validate(api_key, scope="GIGACHAT_API_B2B")

# Slower (up to 3 requests, ~3-6 seconds)
result = await validator.validate(api_key)  # Auto-detect
```

### Supported Providers

- **GigaChat**: Validates key with known scope (v0.8.0) or auto-detects scope (v0.8.1+)
  - Optional `scope` parameter (GIGACHAT_API_PERS/B2B/CORP) - if omitted, auto-detects
  - Supports `verify_ssl` parameter for Russian CA certificates
  - Returns `SCOPE_MISMATCH` if scope doesn't match key type
  - Progress callback `on_scope_attempt` for UI feedback during auto-detection

- **YandexGPT**: Validates IAM token and folder_id permissions (v0.8.0)
  - Requires `folder_id` parameter
  - Uses minimal request (maxTokens: 1) for cost efficiency
  - Extracts request_id from error responses for support

### Error Codes

- `SUCCESS`: Key is valid
- `INVALID_API_KEY`: 401 Unauthorized (invalid or expired key)
- `SCOPE_MISMATCH`: GigaChat scope conflict (400, code:7)
- `PERMISSION_DENIED`: YandexGPT folder_id access denied (403)
- `RATE_LIMIT_EXCEEDED`: 429 Too Many Requests (includes `retry_after`)
- `NETWORK_TIMEOUT`: Request timeout (default: 10s)
- `PROVIDER_ERROR`: 500+ Server error
- `VALIDATION_ERROR`: Unexpected error during validation

### Examples

See [validation_demo.py](examples/validation_demo.py) for complete examples.

## Provider Metrics & Monitoring

Multi-LLM Orchestrator automatically tracks performance metrics for each provider, enabling intelligent routing and monitoring.

### Accessing Metrics

The Router collects aggregated metrics for each provider, including:
- Request counts (total, successful, failed)
- Average latency (for successful requests)
- Rolling average latency (last 100 requests)
- Error rate (recent errors)
- Health status (`healthy`, `degraded`, or `unhealthy`)

```python
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider

router = Router(strategy="best-available")
router.add_provider(MockProvider(ProviderConfig(name="provider1", model="mock-normal")))

# Make some requests
await router.route("Test 1")
await router.route("Test 2")

# Access metrics
metrics = router.get_metrics()
for provider_name, provider_metrics in metrics.items():
    print(f"{provider_name}:")
    print(f"  Health: {provider_metrics.health_status}")
    print(f"  Success rate: {provider_metrics.success_rate:.2%}")
    print(f"  Avg latency: {provider_metrics.avg_latency_ms:.1f}ms")
    print(f"  Rolling avg latency: {provider_metrics.rolling_avg_latency_ms:.1f}ms" if provider_metrics.rolling_avg_latency_ms else "  Rolling avg latency: N/A")
```

### Health Status

Provider health status is determined automatically based on:
- **Error Rate**: High error rates (>30% degraded, >60% unhealthy) indicate provider issues
- **Latency Degradation**: If rolling average latency is significantly higher than overall average, provider is marked as degraded
- **Insufficient Data**: New providers with few requests are optimistically marked as `healthy`

The `best-available` routing strategy uses health status to prioritize providers, always preferring `healthy` over `degraded` over `unhealthy`.

### Structured Logging

Router automatically logs request events with structured fields:
- `llm_request_completed` (info level) for successful requests
- `llm_request_failed` (warning level) for failed requests

Each log entry includes: `provider`, `model`, `latency_ms`, `streaming`, `success`, and `error_type` (for failures).

**Note:** Token-based metrics (token count, tokens/s, cost) are not yet implemented. This is planned for future releases (v0.7.0+).

## Documentation

- **[Architecture Overview](docs/architecture.md)** — System design and components
- **[Contributing Guide](CONTRIBUTING.md)** — How to contribute to the project
- **[Provider Documentation](docs/providers/)** — Detailed provider guides
  - [GigaChat Provider](docs/providers/gigachat.md)
  - [YandexGPT Provider](docs/providers/yandexgpt.md)
  - [Creating Custom Provider](docs/providers/custom_provider.md)
- **[routing_demo.py](examples/routing_demo.py)** — Interactive demonstration of routing strategies and fallback mechanisms

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.