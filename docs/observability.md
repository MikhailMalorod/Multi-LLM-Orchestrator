# Observability Guide

## Overview

Multi-LLM Orchestrator provides comprehensive observability through:
- **Provider-level metrics**: Latency, success rates, health status
- **Token tracking**: Prompt tokens, completion tokens, total tokens
- **Cost estimation**: Real-time cost tracking in RUB (Russian Rubles)
- **Prometheus integration**: HTTP endpoint for monitoring systems

## Token Tracking

### How It Works

The orchestrator automatically tracks token usage for all requests:

1. **Tokenization**: Uses `tiktoken` library for accurate token counting (GPT-like models)
2. **Fallback**: If tiktoken fails, falls back to word-based estimation (`word_count * 1.3`)
3. **Tracking**: Counts both prompt tokens (input) and completion tokens (output)
4. **Aggregation**: Accumulates tokens per provider for lifetime statistics

### Token Counting Methods

```python
from orchestrator.tokenization import count_tokens

# Exact tokenization (via tiktoken)
tokens = count_tokens("Hello, world!")
print(tokens)  # 4 (exact)

# Fallback estimation (if tiktoken unavailable)
tokens = count_tokens("Привет, мир!")  # May fallback to word count * 1.3
```

### Accessing Token Metrics

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import MockProvider, ProviderConfig

async def main():
    router = Router(strategy="round-robin")
    
    # Add provider
    config = ProviderConfig(name="provider-1", model="mock-normal")
    router.add_provider(MockProvider(config))
    
    # Make requests
    for i in range(10):
        await router.route(f"Request {i}")
    
    # Access token metrics
    metrics = router.get_metrics()
    for provider_name, provider_metrics in metrics.items():
        print(f"Provider: {provider_name}")
        print(f"  Total requests: {provider_metrics.total_requests}")
        print(f"  Prompt tokens: {provider_metrics.total_prompt_tokens}")
        print(f"  Completion tokens: {provider_metrics.total_completion_tokens}")
        print(f"  Total tokens: {provider_metrics.total_tokens}")
        print(f"  Total cost: {provider_metrics.total_cost:.2f} RUB")

asyncio.run(main())
```

## Cost Estimation

### Pricing (per 1000 tokens)

**GigaChat**:
- `GigaChat` (base): ₽1.00
- `GigaChat-Pro`: ₽2.00
- `GigaChat-Plus`: ₽1.50
- Default (unknown models): ₽1.50

**YandexGPT**:
- `yandexgpt/latest`: ₽1.50
- `yandexgpt-lite/latest`: ₽0.75
- Default (unknown models): ₽1.50

**Ollama & Mock**:
- Free (₽0.00)

### Cost Calculation

Cost is calculated as: `(total_tokens / 1000) * price_per_1k_tokens`

```python
from orchestrator.pricing import calculate_cost

# GigaChat-Pro example
cost = calculate_cost("gigachat", "GigaChat-Pro", 1500)
print(cost)  # 3.0 RUB (1500 tokens * 2.00 / 1000)

# YandexGPT lite example
cost = calculate_cost("yandexgpt", "yandexgpt-lite/latest", 2000)
print(cost)  # 1.5 RUB (2000 tokens * 0.75 / 1000)
```

### Programmatic Access

```python
# Get cost in real-time
metrics = router.get_metrics()
total_cost = sum(m.total_cost for m in metrics.values())
print(f"Total infrastructure cost: {total_cost:.2f} RUB")
```

## Prometheus Integration

### Starting Metrics Server

```python
import asyncio
from orchestrator import Router

async def main():
    router = Router(strategy="best-available")
    
    # Add providers...
    
    # Start Prometheus HTTP server
    await router.start_metrics_server(port=9090)
    
    # Metrics available at http://localhost:9090/metrics
    
    # Make requests...
    
    # Stop server (graceful shutdown)
    await router.stop_metrics_server()

asyncio.run(main())
```

### Port Configuration

```python
# Default port (9090)
await router.start_metrics_server()

# Custom port (if 9090 is in use)
await router.start_metrics_server(port=9091)
```

### Error Handling

```python
try:
    await router.start_metrics_server(port=9090)
except OSError as e:
    if "already in use" in str(e):
        # Port conflict - use different port
        await router.start_metrics_server(port=9091)
    else:
        raise
```

### Prometheus Configuration

Add this to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'llm-orchestrator'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s
```

Restart Prometheus:
```bash
prometheus --config.file=prometheus.yml
```

### Available Metrics

#### 1. Request Counters
```promql
# Total requests by provider and status
llm_requests_total{provider="gigachat",status="success"}
llm_requests_total{provider="gigachat",status="failure"}
```

#### 2. Latency Histogram
```promql
# Request latency in seconds
llm_request_latency_seconds{provider="gigachat"}
```

#### 3. Token Counters
```promql
# Total tokens processed
llm_tokens_total{provider="gigachat",type="prompt"}
llm_tokens_total{provider="gigachat",type="completion"}
```

#### 4. Cost Counter
```promql
# Total cost in rubles
llm_cost_total{provider="gigachat"}
```

#### 5. Health Gauge
```promql
# Provider health (1=healthy, 0.5=degraded, 0=unhealthy)
llm_provider_health{provider="gigachat"}
```

### Example Queries

#### Request Rate (requests/sec)
```promql
rate(llm_requests_total[5m])
```

#### Success Rate (%)
```promql
sum(rate(llm_requests_total{status="success"}[5m])) /
sum(rate(llm_requests_total[5m])) * 100
```

#### Average Latency (seconds)
```promql
rate(llm_request_latency_seconds_sum[5m]) /
rate(llm_request_latency_seconds_count[5m])
```

#### Total Cost per Provider (RUB)
```promql
llm_cost_total
```

#### Tokens per Second
```promql
rate(llm_tokens_total[5m])
```

#### Unhealthy Providers
```promql
llm_provider_health < 1.0
```

#### Cost Rate (RUB/min)
```promql
rate(llm_cost_total[1m]) * 60
```

### Grafana Dashboard

Create a Grafana dashboard with these panels:

**Panel 1: Request Rate**
- Query: `rate(llm_requests_total[5m])`
- Type: Graph
- Legend: `{{provider}} - {{status}}`

**Panel 2: Success Rate**
- Query: `sum(rate(llm_requests_total{status="success"}[5m])) / sum(rate(llm_requests_total[5m])) * 100`
- Type: Gauge
- Unit: Percent (0-100)

**Panel 3: Latency (p50, p95, p99)**
- Query p50: `histogram_quantile(0.5, rate(llm_request_latency_seconds_bucket[5m]))`
- Query p95: `histogram_quantile(0.95, rate(llm_request_latency_seconds_bucket[5m]))`
- Query p99: `histogram_quantile(0.99, rate(llm_request_latency_seconds_bucket[5m]))`
- Type: Graph

**Panel 4: Token Usage**
- Query: `rate(llm_tokens_total[5m])`
- Type: Graph
- Legend: `{{provider}} - {{type}}`

**Panel 5: Cost Tracking**
- Query: `llm_cost_total`
- Type: Stat
- Unit: Currency (RUB)

**Panel 6: Provider Health**
- Query: `llm_provider_health`
- Type: Status History
- Thresholds: 0 (red), 0.5 (yellow), 1 (green)

## Troubleshooting

### Port Already in Use

**Error**:
```
OSError: Port 9090 is already in use
```

**Solutions**:
```python
# Option 1: Use different port
await router.start_metrics_server(port=9091)

# Option 2: Find and stop conflicting process
# Linux/Mac: lsof -i :9090
# Windows: netstat -ano | findstr :9090
```

### High Token Counts (Fallback Warning)

**Warning in logs**:
```
WARNING: tiktoken failed for model 'xxx': ... Using fallback estimation
```

**Causes**:
- tiktoken not installed
- Unsupported model encoding
- Special characters in text

**Solutions**:
```bash
# Install tiktoken
pip install tiktoken

# Or accept approximate counts (fallback is reasonable)
```

### Metrics Not Updating

**Issue**: Metrics at `/metrics` endpoint are stale

**Causes**:
- Metrics update every 1 second in background task
- Wait 1-2 seconds after requests

**Verification**:
```python
import asyncio

# Make request
await router.route("Hello")

# Wait for metrics update
await asyncio.sleep(2)

# Check metrics
metrics = router.get_metrics()
```

### Server Won't Stop

**Issue**: `stop_metrics_server()` hangs

**Solution**:
```python
# Ensure proper cleanup in exception handlers
try:
    await router.start_metrics_server()
    # ... do work ...
except Exception as e:
    print(f"Error: {e}")
finally:
    await router.stop_metrics_server()  # Always cleanup
```

### Memory Concerns (Streaming)

**Issue**: Large responses consume memory during streaming

**Explanation**: 
- Orchestrator accumulates chunks for token counting
- This is necessary for accurate token tracking

**Memory Usage**:
- Typical LLM response: 500-2000 tokens ≈ 2-10 KB
- Large response: 4000 tokens ≈ 20 KB
- Acceptable for most use cases

**Mitigation** (if needed):
```python
# For very large responses, consider:
# 1. Use non-streaming route() for small responses
# 2. Accept approximate token counts for streaming
# 3. Implement custom chunking logic
```

## Best Practices

### 1. Always Stop Metrics Server

```python
async def main():
    router = Router()
    
    try:
        await router.start_metrics_server()
        # ... work ...
    finally:
        await router.stop_metrics_server()  # Cleanup
```

### 2. Monitor Cost in Production

```python
# Set up alerts in Prometheus
# Alert if cost exceeds threshold
groups:
  - name: llm-cost-alerts
    rules:
      - alert: HighLLMCost
        expr: rate(llm_cost_total[1h]) > 100  # 100 RUB/hour
        for: 5m
        annotations:
          summary: "LLM costs are high"
```

### 3. Use Appropriate Ports

```python
# Production: Use standard Prometheus port
await router.start_metrics_server(port=9090)

# Development: Use custom port to avoid conflicts
await router.start_metrics_server(port=19090)
```

### 4. Structured Logging

```python
import logging

# Enable structured logging for cost tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Logs will include token and cost info:
# INFO - orchestrator.router - llm_request_completed - 
#   provider=gigachat, tokens=1500, cost_rub=3.00
```

## Next Steps

- Set up Prometheus and Grafana
- Create custom dashboards for your use case
- Set up alerts for cost thresholds
- Monitor provider health and latency
- Optimize token usage based on metrics

For more examples, see [examples/prometheus_demo.py](../examples/prometheus_demo.py).
