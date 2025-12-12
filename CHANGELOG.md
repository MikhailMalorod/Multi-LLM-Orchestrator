# Changelog

All notable changes to Multi-LLM Orchestrator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Added: `tiktoken` ^0.5.2
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
