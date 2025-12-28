Create a comprehensive strategic document for Multi-LLM Orchestrator project.

FILE: STRATEGY.md (in root directory)

Structure the document with the following sections:

# Multi-LLM Orchestrator: Strategy & Roadmap

## Recent Updates

### v0.7.0 (Completed) - Released: December 13, 2025 ✅

**Goal:** Advanced observability with token-aware metrics and Prometheus integration

**Implemented Features:**

- **Token-aware Metrics (Minimal Scope):**
  - ✅ Prompt token count tracking
  - ✅ Completion token count tracking  
  - ✅ Total tokens calculation (computed property)
  - ✅ Cost estimation for GigaChat and YandexGPT (fixed pricing)
  - ✅ `tiktoken ^0.12.0` integration with pre-built wheels for Windows
  - ✅ Fallback to word-based estimation (`len(text.split()) * 1.3`)
  - ✅ Automatic tokenization in `Router.route()` and `Router.route_stream()`
  - ❌ Provider-specific tokenizers (deferred to v0.8.0)
  - ❌ SentencePiece for Ollama (deferred to v0.8.0)

- **Prometheus HTTP Endpoint:**
  - ✅ `/metrics` endpoint with standard Prometheus text format
  - ✅ `aiohttp` lightweight HTTP server (background task)
  - ✅ Metrics export: `llm_requests_total`, `llm_request_latency_seconds`, `llm_tokens_total`, `llm_cost_total`, `llm_provider_health`
  - ✅ Auto-updating metrics loop (1 second interval)
  - ✅ `Router.start_metrics_server()` and `Router.stop_metrics_server()` methods
  - ❌ Push to Prometheus Pushgateway (deferred to v0.8.0)

- **Enhanced ProviderMetrics:**
  - ✅ Extension of existing `ProviderMetrics` class (100% backward compatible)
  - ✅ New fields: `total_prompt_tokens`, `total_completion_tokens`, `total_cost`
  - ✅ `total_tokens` computed property
  - ✅ Updated `record_success()` with optional token/cost parameters
  - ✅ Per-request token tracking in Router (both regular and streaming)

- **Cost Calculation:**
  - ✅ `pricing.py` module with unified pricing (RUB per 1k tokens)
  - ✅ Support for GigaChat models (GigaChat, GigaChat-Pro, GigaChat-Plus)
  - ✅ Support for YandexGPT models (yandexgpt/latest, yandexgpt-lite/latest)
  - ✅ Prefix matching for provider variants (e.g., "mock-1" → "mock")
  - ✅ Free pricing for Ollama and Mock providers

- **Quality & Testing:**
  - ✅ Test coverage: 81% (203 tests passed, 4 skipped)
  - ✅ Unit tests for tokenization logic (12 tests)
  - ✅ Unit tests for pricing calculation (25 tests)
  - ✅ Unit tests for Prometheus exporter
  - ✅ Integration tests for metrics tracking
  - ✅ mypy strict mode: 0 errors
  - ✅ ruff linting: all checks passed

- **Documentation:**
  - ✅ `README.md` — new section "Observability & Metrics"
  - ✅ `CHANGELOG.md` — v0.7.0 release notes
  - ✅ `docs/observability.md` — comprehensive 200+ line guide
  - ✅ `examples/prometheus_demo.py` — working example with mock providers

- **New Dependencies:**
  - ✅ `prometheus-client = "^0.19.0"`
  - ✅ `tiktoken = "^0.12.0"` (pre-built wheels for Windows)
  - ✅ `aiohttp = "^3.9.1"`

**Development Timeline:**
- December 12-13: Scope definition and planning ✅
- December 13: Full implementation sprint ✅
  - Core modules: tokenization.py, pricing.py, prometheus_exporter.py
  - Router integration for token/cost tracking
  - Comprehensive test suite (65+ new tests)
  - Documentation and examples
- December 13: Bug fixes ✅
  - Fixed HTTP 500 on /metrics endpoint (charset conflict)
  - Fixed "Unknown provider" warnings (prefix matching)
  - Updated tiktoken to v0.12.0 (Windows compatibility)

**Status:** ✅ Completed and Production-Ready (December 13, 2025)

**Key Achievements:**
- 4 new modules: `tokenization.py`, `pricing.py`, `prometheus_exporter.py`, plus Router enhancements
- 65+ new tests (tokenization: 12, pricing: 25, metrics integration: 5, Prometheus: 12+)
- Zero breaking changes (100% backward compatibility)
- Type-safe (mypy strict) and lint-clean (ruff)
- Comprehensive documentation (200+ lines in observability.md)
- Working example with real-time metrics visualization

**Target Audience:** DevOps engineers, data engineers, and teams requiring production observability for LLM workloads


### v0.7.5 (December 28, 2025) ✅

**Goal:** Zero-downtime provider updates for production environments

**Implemented Features:**
- ✅ `Router.update_providers()` method
  - Zero-downtime provider swap (point-in-time semantics)
  - Optional metrics preservation (`preserve_metrics` parameter)
  - Validation (empty list, duplicate names)
  - Model change detection (WARNING log)
  - Atomic swap with round-robin index reset
- ✅ Race condition fix in `route()` and `route_stream()`
  - Safe metrics access with on-the-fly creation
  - Active requests complete successfully during provider updates
- ✅ 8 comprehensive tests (100% passed)
- ✅ Full backward compatibility

**Quality:**
- Type checking (mypy): 0 errors
- Linting (ruff): 0 warnings  
- Tests: 226 passed, 4 skipped
- Documentation: Google-style docstrings

**Use Case:** Platform SaaS (Managed→BYOK migrations, API key rotation)

**Development Timeline:**
- December 28: Feature request from Platform SaaS Team (Issue #5)
- December 28: Full implementation sprint (analysis, implementation, testing)
- December 28: Released same day (досрочно, дедлайн был 4 января)

**Status:** ✅ Completed and Production-Ready (December 28, 2025)

**Key Achievements:**
- 1 new method: `Router.update_providers()`
- 8 new tests (all passing)
- Race condition fix (production-critical)
- Zero breaking changes (100% backward compatibility)
- Complete same-day delivery (7 days ahead of deadline)

**Target Audience:** Platform SaaS teams requiring zero-downtime configuration updates


### v0.7.6 (January 10, 2026) ✅

**Goal:** Hybrid usage callback API for billing and analytics integration

**Implemented Features:**
- ✅ `UsageData` dataclass with comprehensive usage information
  - Provider name, model, tokens (prompt/completion/total)
  - Cost (RUB), latency (ms), success status
  - Streaming flag, error type, timestamp
- ✅ Python callback support via `usage_callback` parameter
  - Async function receives `UsageData` instance
  - Useful for in-process analytics and logging
- ✅ HTTP POST callback support via `callback_url` parameter
  - Remote billing API integration (Platform SaaS use case)
  - Optional `tenant_id` and `platform_key_id` context fields
  - 5-second timeout, fail-silent behavior
- ✅ `_invoke_usage_callback()` helper method
  - Handles both Python and HTTP callbacks
  - Fail-silent: callback errors don't disrupt requests
- ✅ Full integration in `route()` and `route_stream()`
  - Callback invoked for success and error paths
  - Complete fallback support: callback for each provider attempt
- ✅ 15 comprehensive tests (100% passed)
  - Python callback: success, error, streaming, fallback, error handling
  - HTTP callback: success, error, tenant/key context, timeout, network errors
  - Validation: mutual exclusivity, optional parameters
- ✅ Full backward compatibility (all parameters optional)

**Quality:**
- Type checking (mypy): 0 errors (strict mode)
- Linting (ruff): 0 warnings
- Tests: 241 passed (15 new tests for usage callbacks)
- Coverage: 88% for router.py (new methods covered)
- Documentation: Google-style docstrings, README examples, CHANGELOG

**Use Case:** Platform SaaS (Managed/BYOK billing, cost transparency, analytics)

**Development Timeline:**
- January 10: Feature request from Platform SaaS Team (Issue #7)
- January 10: Full implementation sprint (analysis, implementation, testing)
- January 10: Released same day (2 days ahead of Week 3 deadline)

**Status:** ✅ Completed and Production-Ready (January 10, 2026)

**Key Achievements:**
- Hybrid API: Python callback + HTTP POST callback
- Complete audit trail: callback for each provider in fallback chain
- Fail-silent behavior: robust error handling
- Zero breaking changes (100% backward compatibility)
- Delivered 2 days ahead of schedule (Week 3 deadline: Jan 12-18)

**Business Impact:**
- Platform SaaS can proceed with Week 3 roadmap
- ~20k₽ MRR impact (cost transparency → BYOK conversion)
- Zero disruption to existing users

**Related:** Issue #7, PR #8

**Target Audience:** Platform SaaS teams requiring billing/analytics integration


### v0.6.0 (Current Release)
- ✅ Provider-level metrics tracking (latency, success/failure rates, health status)
- ✅ New routing strategy `best-available` (health + latency aware)
- ✅ `ProviderMetrics` class with rolling window latency and error rate tracking
- ✅ Automatic health status determination (`healthy`, `degraded`, `unhealthy`)
- ✅ Structured logging for request events (`llm_request_completed`, `llm_request_failed`)
- ✅ `Router.get_metrics()` method for accessing provider metrics
- ✅ Comprehensive tests for metrics and smart routing (14 new tests for metrics, 5 for best-available)
- ✅ Updated documentation with metrics and best-available examples

### v0.5.0 (November 29, 2025)
- ✅ Added streaming support for incremental text generation
- ✅ Implemented `generate_stream()` method in BaseProvider with default fallback
- ✅ Added `route_stream()` method in Router with fallback logic (before first chunk)
- ✅ Streaming support in MockProvider (word-by-word streaming)
- ✅ Streaming support in GigaChatProvider with SSE (Server-Sent Events) parsing
- ✅ LangChain streaming methods: `_stream()` (sync) and `_astream()` (async)
- ✅ Comprehensive streaming tests (17 new tests)
- ✅ Created streaming demo examples
- ✅ Updated documentation with streaming examples

### v0.4.0 (November 25, 2025)
- ✅ Added LangChain compatibility layer
- ✅ MultiLLMOrchestrator wrapper for LangChain integration
- ✅ Support for sync/async LangChain chains
- ✅ 18 comprehensive tests for LangChain compatibility
- ✅ Updated README with LangChain examples
- ✅ Created examples/langchain_demo.py

### v0.2.0 (November 23, 2025)
- ✅ Added YandexGPTProvider with IAM authentication
- ✅ Support for yandexgpt/latest and yandexgpt-lite/latest models
- ✅ Added folder_id parameter to ProviderConfig
- ✅ 23 comprehensive tests for YandexGPT (88% coverage)
- ✅ Updated README with YandexGPT examples
- ✅ Published to PyPI as v0.2.0

### v0.3.1 (November 25, 2025)
- ✅ Added OllamaProvider for local LLM models
- ✅ Support for Llama 3, Mistral, Phi and other Ollama models
- ✅ No API keys required for local inference
- ✅ 18 comprehensive tests for OllamaProvider (99 total tests)
- ✅ Created docs/providers/ollama.md documentation
- ✅ Updated README with Ollama examples
- ✅ Fixed linting issues in example tests

### v0.2.1 (November 24, 2025)
- ✅ Added `verify_ssl` parameter to ProviderConfig
- ✅ Fixed SSL certificate verification issues with GigaChat (Russian CA)
- ✅ Added security warnings for disabled SSL verification
- ✅ Updated documentation with examples
- ✅ Removed manual SSL verification hacks from codebase

## 1. Vision & Mission
- Vision: What we're building and why it matters
- Mission: Our approach to achieving the vision
- Target audience: Russian developers working with AI
- Unique value proposition: Unified interface for Russian LLMs with smart routing

## 2. Market Analysis
- Current problems:
  - Companies forced to choose between GigaChat/YandexGPT/local models
  - No unified API
  - Complex integration and fallback logic
  - Compliance challenges (152-ФЗ)
- Market opportunity:
  - Russian AI market size: ₽168 billion (2025), growing 45% YoY
  - 10k-50k Python developers working with AI
  - Enterprise demand for import substitution solutions
- Competitive landscape:
  - LangChain (not Russia-focused)
  - Direct API usage (complex, no routing)
  - Whitespace: No unified orchestrator for Russian LLMs

## 3. Product Roadmap

### Phase 1: MVP (Weeks 1-4) - ✅ COMPLETED
Goal: Working prototype with core functionality

Week 1-2: Foundation
- [x] Project structure
- [x] Base provider abstraction
- [x] Mock provider for testing
- [x] Basic router with rule-based strategies
- [x] Configuration management

Week 3: First Real Provider
- [x] GigaChat integration (OAuth2, API wrapper) ✅
- [x] Health checks and retry logic ✅ (implemented in base.py)
- [x] Example scripts ✅ (routing_demo.py, simple_chat.py)

Week 4: Routing Demo
- [x] Multiple routing strategies (round-robin, random, first-available) ✅
- [x] Fallback mechanism ✅
- [x] Rich CLI output ✅
- [x] README with quickstart ✅

Deliverable: Working MVP, GitHub repo with 20-50 stars

**Status:** ✅ Completed November 23, 2025

**Key achievements:**
- Full-featured Router with 3 strategies + fallback
- GigaChatProvider with OAuth2 (20 tests, 100% passing)
- MockProvider with 5 simulation modes
- 56 unit tests with 87% code coverage
- Comprehensive documentation (README, docstrings, examples)

### Phase 2: Community Building (Month 2) - In Progress
Goal: Get first 100 users and feedback

**Week 5: Quality & PyPI Release** ✅ **COMPLETED November 23, 2025**
- [x] Type checking with mypy (strict mode, 0 errors) ✅
- [x] Code quality: ruff linting (0 warnings) ✅
- [x] pytest coverage >70% (maintained at 88%) ✅
- [x] Prepare for PyPI publication ✅
  - [x] Update pyproject.toml (version 0.1.0, metadata) ✅
  - [x] Create GitHub Action for automated releases ✅
  - [x] Add badges (build, coverage, PyPI version, tests) ✅
  - [x] Create py.typed for type hints support ✅
  - [x] Publish to PyPI ✅ (v0.1.0 published November 23, 2025)
- [x] Update documentation for production use ✅

**Deliverable:** ✅ Production-ready package ready for PyPI, 88% test coverage

**Key achievements:**
- Fixed 101 mypy errors (strict mode compliance)
- Fixed 272 ruff warnings (code quality)
- Coverage maintained at 88% (above 87% target)
- All metadata updated for PyPI publication
- GitHub Action configured for automated publishing
- Badges added to README (PyPI, Coverage, Tests)

**Week 6: YandexGPT Provider** ✅ **COMPLETED November 23, 2025**
- [x] Study YandexGPT API (IAM auth, endpoints) ✅
- [x] Implement YandexGPTProvider class ✅
- [x] Add 20+ tests for YandexGPT ✅ (23 tests added, 88% coverage)
- [x] Update README with YandexGPT examples ✅
- [x] Update env.example ✅

**Deliverable:** ✅ Second real LLM provider, published as v0.2.0 on PyPI

**Key achievements:**

- Full YandexGPT integration with IAM authentication
- Support for two models (yandexgpt/latest, yandexgpt-lite/latest)
- Extended ProviderConfig with folder_id parameter
- 23 comprehensive tests with 88% code coverage
- Published to PyPI (v0.2.0)
- Documentation updated with YandexGPT examples

**Week 7-8: Marketing & Community**

Technical:
- [x] Project reorganization ✅ (November 25, 2025)
  - [x] Created docs/ structure with architecture documentation ✅
  - [x] Created CONTRIBUTING.md with development guidelines ✅
  - [x] Moved test_real_*.py to examples/real_tests/ ✅
  - [x] Removed temporary files (plan*.md, *_QUESTIONS.md) ✅
  - [x] Created provider documentation (docs/providers/) ✅
- [x] SSL verification control (v0.2.1) ✅
  - [x] Added verify_ssl parameter to ProviderConfig ✅
  - [x] Fixed GigaChat SSL issues with Russian CA ✅
- [x] Ollama integration (local models) ✅ (November 25, 2025)
- [x] LangChain compatibility layer ✅ (November 25, 2025)
- [x] Streaming support (v0.5.0) ✅ (November 29, 2025)
  - [x] BaseProvider.generate_stream() with default fallback ✅
  - [x] Router.route_stream() with smart fallback ✅
  - [x] MockProvider and GigaChatProvider streaming ✅
  - [x] LangChain streaming (_stream, _astream) ✅
  - [x] 17 comprehensive streaming tests ✅
- [x] Observability & Smart Routing (v0.6.0) ✅ (December 2025)
  - [x] ProviderMetrics class with latency and error tracking ✅
  - [x] Health status determination (healthy/degraded/unhealthy) ✅
  - [x] best-available routing strategy ✅
  - [x] Structured logging for request events ✅
  - [x] Metrics integration in Router ✅
  - [x] Comprehensive tests for metrics and routing ✅

Marketing:
- [x] Article on Habr (v0.5.0 published December 3, 2025) ✅
- [x] Post on Habr (v0.6.0 published December 5, 2025) ✅
- [x] Response to community feedback (LiteLLM comparison) ✅
- [x] Habr contest invitation received ("ИИ в разработке", deadline Jan 16) ✅
- [ ] Telegram outreach (2-3 channels) - in progress
- [ ] Habr contest article - planned for Dec 6-8


Deliverable: 100-300 GitHub stars, 5-10 production users

### Phase 3: Monetization (Month 3-4)
Goal: First paying customers

Technical:
- [ ] Managed cloud version (FastAPI + Docker)
- [ ] Cost tracking and analytics
- [ ] Advanced observability (token-aware metrics, Prometheus export)
- [ ] Web UI for monitoring

Business:
- [ ] Freemium pricing: 1000 requests/month free
- [ ] Pro tier: ₽1,990/month (10k requests)
- [ ] Enterprise tier: custom pricing
- [ ] First 3-5 paying customers

Deliverable: ₽15k-50k MRR

### Phase 4: Scale (Month 5-6)
Goal: Become standard tool for Russian AI developers

Technical:
- [ ] Plugin system for custom providers
- [ ] Advanced routing (ML-based)
- [ ] Multi-agent orchestration
- [ ] Integration marketplace

Business:
- [ ] Partnership with Yandex/Sber
- [ ] Channel partnerships (integrators)
- [ ] Enterprise sales pipeline
- [ ] 50-100 paying customers

Deliverable: ₽200k-500k MRR, industry recognition

## 4. Go-to-Market Strategy

### Distribution Channels
1. Developer Communities:
   - Habr (articles, tutorials)
   - Telegram (Russian AI channels)
   - GitHub (opensource)
   - Conferences (Sber Conf, OpenSourceDay, HighLoad)

2. Content Marketing:
   - Technical blog posts (1-2 per month)
   - Video tutorials on YouTube
   - Case studies from early adopters
   - Documentation and guides

3. Partnerships:
   - LLM providers (Yandex, Sber) - official integration
   - Cloud providers (Yandex Cloud, VK Cloud) - marketplace listing
   - System integrators - reseller partnerships

4. Community Building:
   - Active GitHub presence
   - Discord/Telegram community
   - Monthly online meetups
   - Contributors program

### Pricing Strategy
- Freemium core (opensource)
- Managed cloud (SaaS pricing)
- Enterprise support (high-touch sales)
- Consulting services (implementation)

## 5. Success Metrics

### Developer Adoption (Leading Indicators)
- GitHub stars: 100 (Month 1) → 500 (Month 3) → 1000 (Month 6)
- Weekly active users: 50 → 200 → 500
- PyPI downloads: 100/week → 500/week → 2000/week

### Business Metrics (Lagging Indicators)
- Paying customers: 0 → 5 → 20 → 50
- MRR: ₽0 → ₽50k → ₽200k → ₽500k
- Enterprise deals: 0 → 1 → 3 → 5

### Quality Metrics
- Test coverage: >70%
- Documentation completeness: >90%
- Issue response time: <24 hours
- PR merge time: <48 hours

## 6. Risk Mitigation

### Technical Risks
- Risk: Yandex/Sber release unified API → Our solution becomes obsolete
  Mitigation: Focus on value-add (routing, observability, compliance)

- Risk: LangChain adds Russian integrations
  Mitigation: Be lightweight and Russia-specific, move faster

### Business Risks
- Risk: Low willingness to pay
  Mitigation: Freemium model, prove value first

- Risk: Cannot compete with enterprise sales
  Mitigation: Partner with integrators, focus on PLG

### Operational Risks
- Risk: Solo founder burnout (1-2 hours/day limit)
  Mitigation: Community-driven development, find co-founder

- Risk: Support overhead kills productivity
  Mitigation: Self-service docs, community support, paid support tier

## 7. Decision Framework

When to pivot:
- <50 GitHub stars after 2 months
- No paying customers after 4 months
- Competitor launches superior solution

When to double down:
- 300+ GitHub stars in first 2 months
- 5+ enterprise inquiries
- Strong organic growth (>20% week-over-week)

When to seek funding/co-founder:
- PMF achieved (40% "very disappointed" metric)
- ₽200k+ MRR with clear path to ₽1M
- Need to scale faster than competition

## 8. Next Actions (Immediate)

Week 1 (Current):
- [x] Create project structure
- [x] Implement base provider abstraction
- [x] Create mock provider
- [x] Implement basic router

Week 2:
- [x] Integrate GigaChat ✅
- [x] Create routing demo ✅
- [x] Write comprehensive README ✅
- [x] First commit and push ✅

Week 5 (November 23-26, 2025): ✅ **COMPLETED**
- [x] Run mypy --strict and fix all type errors ✅ (101 errors fixed)
- [x] Run ruff check and fix all linting issues ✅ (272 warnings fixed)
- [x] Verify pytest coverage >70% ✅ (88% achieved)
- [x] Update pyproject.toml for PyPI (version, description, keywords) ✅
- [x] Create GitHub Action for PyPI publishing ✅
- [x] Add badges to README (build status, coverage, PyPI) ✅
- [x] Create py.typed for type hints support ✅
- [x] Publish v0.1.0 to PyPI (ready, needs GitHub release) ✅

Week 6 (November 23, 2025): ✅ **COMPLETED**
- [x] Study YandexGPT API documentation ✅
- [x] Implement YandexGPTProvider ✅
- [x] Add tests for YandexGPT (23 scenarios) ✅
- [x] Update documentation ✅
- [x] Publish v0.2.0 to PyPI ✅

Week 7-8 (December 1-8, 2025):
- [ ] Write Habr article (2000+ words)
- [ ] Post in Russian AI communities (Telegram, Reddit)
- [ ] Get feedback from 5-10 developers
- [ ] Iterate based on feedback
- [ ] Reddit r/LocalLLaMA post — Dec 6-7
- [ ] Reddit r/LLMDevs post — Dec 9-10  
- [ ] Track Reddit → PyPI conversion

---

---

## 🎯 Current Status Summary

**Phase 1 (MVP):** ✅ Completed (November 23, 2025)

**Phase 2 (Community Building):** ⏳ In Progress

- Week 5 (Quality & PyPI): ✅ Completed (November 23, 2025) - v0.1.0 published
- Week 6 (YandexGPT): ✅ Completed (November 23, 2025) - v0.2.0 published
- Week 7 (Bugfixes & Docs): ✅ Completed (November 25, 2025) - v0.2.1 published, docs created
- Week 8 (Marketing): ⏳ In Progress - Habr article submitted
- Observability & Smart Routing (v0.6.0): ✅ Completed (December 2025) - Metrics and best-available strategy implemented
- **Token-aware Metrics & Prometheus (v0.7.0): ✅ Completed (December 13, 2025) - Full observability stack with cost tracking**

**Latest version:** v0.7.1 (December 23, 2025) ✅

**v0.7.1 (Bugfix Release):**
- Fixed charset conflict in /metrics endpoint
- Fixed prefix matching for provider variants (mock-1, gigachat-dev, etc.)
- Updated tiktoken to 0.12.0 (Windows compatibility)
- 210 tests passed, 82% coverage
- Published: GitHub + PyPI ✅

**Ready for:**

- ✅ Production use (4 providers: GigaChat, YandexGPT, Ollama, Mock)
- ✅ Token-aware metrics with Prometheus integration
- ✅ Provider health monitoring + smart routing
- ✅ Streaming support + LangChain integration
- ✅ Windows compatibility (pre-built wheels)
- ✅ Backward compatible with v0.7.0

## Completed: v0.7.0 (Token-aware Metrics & Prometheus Integration) ✅

**Implemented Features:**

- **Token-aware Metrics:**
  - ✅ Prompt token count tracking
  - ✅ Response/completion token count tracking
  - ✅ Cost estimation based on token usage (RUB per 1k tokens)
  - ✅ Automatic tracking in Router for all requests

- **Tokenization Support:**
  - ✅ `tiktoken ^0.12.0` integration for GPT-like models
  - ✅ Word-based fallback estimation (`len(text.split()) * 1.3`)
  - ✅ Graceful degradation when tiktoken unavailable
  - ❌ Provider-specific tokenizers (deferred to v0.8.0)

- **Cost Calculation:**
  - ✅ Unified pricing module (`pricing.py`)
  - ✅ GigaChat pricing (GigaChat, GigaChat-Pro, GigaChat-Plus)
  - ✅ YandexGPT pricing (latest, lite)
  - ✅ Free pricing for Ollama and Mock
  - ✅ Provider variant matching (e.g., "mock-1" → "mock")

- **Prometheus Export:**
  - ✅ HTTP `/metrics` endpoint (Prometheus text format)
  - ✅ Metrics: requests, latency, tokens, cost, health
  - ✅ Background auto-update task (1s interval)
  - ✅ `aiohttp` lightweight server
  - ✅ Start/stop lifecycle management

**Quality Metrics:**
- ✅ 203 tests passed (65+ new tests for v0.7.0)
- ✅ 81% test coverage
- ✅ mypy strict: 0 errors
- ✅ ruff: all checks passed
- ✅ 100% backward compatibility

## Planned: v0.8.0 (Advanced Tokenization & Analytics)

**Proposed Features:**

- **Advanced Tokenization:**
  - Provider-specific tokenizers (GigaChat, YandexGPT native)
  - SentencePiece for Ollama models
  - Accurate token counting per model

- **Enhanced Observability:**
  - Detailed latency percentiles (p50, p95, p99)
  - Per-model breakdown of metrics
  - Request size distribution
  - Prometheus Pushgateway support

- **Cost Analytics:**
  - Dynamic pricing updates
  - Cost per model/provider breakdown
  - Budget alerts and limits

**Note:** Token-aware metrics successfully implemented in v0.7.0, providing foundation for advanced analytics in v0.8.0.

---
---

## 🏆 December 2025: Habr Contest "ИИ в разработке"

**Deadline:** January 16, 2025  
**Prize pool:** 
- Top-5 authors: 50,000 ₽ each
- Next 10 authors: 25,000 ₽ each

**Planned article:** "Как создать production-ready библиотеку для российских LLM: от MVP до observability"

**Key points:**
- Journey through 6 releases (v0.1.0 → v0.6.0)
- Architecture: BaseProvider, Router, strategies, metrics
- Production challenges: OAuth2, IAM, SSL, streaming
- Results: 6K+ views, community feedback, PyPI publication

**Timeline:**
- December 5: Contest invitation received from Habr editor (Yulia Yunosheva)
- December 6-8: Write article draft (planned)
- December 9-10: Review, edits, publication (planned)
- January 16: Contest deadline

**Status:** ⏳ Concept confirmed, draft in progress

---

Last updated: December 23, 2025 (v0.7.1 Release)
Review frequency: Weekly (every Sunday)
Owner: Mikhail Malorod