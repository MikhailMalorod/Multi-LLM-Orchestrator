# Changelog

All notable changes to Multi-LLM Orchestrator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
