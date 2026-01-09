# v0.7.0 Observability Testing

## What's New in v0.7.0

- **Token Tracking**: Automatic counting of prompt and completion tokens
- **Cost Estimation**: Real-time cost calculation in RUB (₽)
- **Prometheus Metrics**: HTTP `/metrics` endpoint for monitoring
- **Enhanced Metrics**: Extended `ProviderMetrics` with token/cost fields
- **Streaming Support**: Token tracking works with streaming responses

## Running v0.7.0 Tests

```bash
# Run observability tests:
python examples/real_tests/test_v070_observability.py
```

## Prerequisites

Create `.env` file in project root:

```env
GIGACHAT_API_KEY=your_gigachat_key_here
YANDEXGPT_API_KEY=your_yandex_iam_token_here
YANDEXGPT_FOLDER_ID=your_folder_id_here
```

**Note:** Tests will skip gracefully if credentials are missing.

## Test Coverage

### 1. Token Tracking (GigaChat)
**What it tests:**
- ✅ Prompt token counting with `tiktoken`
- ✅ Completion token counting
- ✅ Total tokens calculation (computed property)
- ✅ Cost calculation (GigaChat pricing: ₽1.00/1k tokens)

**Expected output:**
```
📊 Token Tracking Results:
   Prompt Tokens:     45
   Completion Tokens: 120
   Total Tokens:      165
   Cost:              0.1650 RUB

✅ Token tracking working correctly
```

### 2. Token Tracking (YandexGPT)
**What it tests:**
- ✅ Token tracking with different provider
- ✅ YandexGPT pricing verification (₽1.50/1k tokens for latest)
- ✅ Proper provider name matching in `pricing.py`

**Expected output:**
```
📊 Token Tracking Results:
   Prompt Tokens:     38
   Completion Tokens: 95
   Total Tokens:      133
   Cost:              0.1995 RUB

✅ Token tracking working correctly
```

### 3. Streaming with Tokens
**What it tests:**
- ✅ Token counting in streaming mode
- ✅ Cost calculation for streamed responses
- ✅ Metrics updated after stream completion

**Expected output:**
```
📥 Response (streaming): [chunks printed in real-time]

📊 Streaming Token Results:
   Total Tokens: 87
   Cost:         0.0870 RUB

✅ Streaming token tracking working
```

### 4. Prometheus Endpoint
**What it tests:**
- ✅ HTTP server lifecycle (`start_metrics_server`, `stop_metrics_server`)
- ✅ Metrics export format (Prometheus text format)
- ✅ Real-time metric updates (1-second interval)
- ✅ All 5 metric types exported correctly

**Expected output:**
```
✅ Metrics server started at http://localhost:9091/metrics

📊 Prometheus endpoint is running
   Open http://localhost:9091/metrics in browser to verify
   Expected metrics:
   - llm_requests_total
   - llm_request_latency_seconds
   - llm_tokens_total
   - llm_cost_total
   - llm_provider_health

⏸️  Server running for 10 seconds for manual verification...

✅ Metrics server stopped
```

**Manual verification:**
1. During the 10-second window, open: http://localhost:9091/metrics
2. Verify Prometheus format output:
```
# HELP llm_requests_total Total number of LLM requests
# TYPE llm_requests_total counter
llm_requests_total{provider="gigachat",status="success"} 1.0

# HELP llm_tokens_total Total tokens processed
# TYPE llm_tokens_total counter
llm_tokens_total{provider="gigachat",type="prompt"} 45.0
llm_tokens_total{provider="gigachat",type="completion"} 120.0

# HELP llm_cost_total Total cost in rubles
# TYPE llm_cost_total counter
llm_cost_total{provider="gigachat"} 0.165
```

## Expected Results

All 4 tests should pass (or skip if credentials missing):

```
📊 TEST SUMMARY
======================================================================
   ✅ PASS  GigaChat Token Tracking
   ✅ PASS  YandexGPT Token Tracking
   ✅ PASS  Streaming Token Tracking
   ✅ PASS  Prometheus Endpoint
======================================================================
   Total: 4/4 tests passed
======================================================================

🎉 All tests passed! v0.7.0 is ready for release!
```

## Troubleshooting

### Issue: Tokens are 0

**Symptoms:**
```
Prompt Tokens:     0
Completion Tokens: 0
Total Tokens:      0
Cost:              0.0000 RUB
```

**Solutions:**
1. Check `tiktoken` installation:
   ```bash
   pip show tiktoken
   # Should be version 0.12.0 or higher
   ```

2. Reinstall if needed:
   ```bash
   pip install --upgrade tiktoken
   ```

3. Verify fallback works:
   ```python
   from orchestrator.tokenization import count_tokens
   count_tokens("test")  # Should return non-zero value
   ```

### Issue: Cost is 0.00

**Symptoms:**
```
Total Tokens:      150
Cost:              0.0000 RUB  # ❌ Wrong!
```

**Solutions:**
1. Check provider name matches `pricing.py`:
   - **GigaChat**: name must be exactly `"gigachat"` (lowercase)
   - **YandexGPT**: name must be exactly `"yandexgpt"` (lowercase)

2. Verify pricing module:
   ```bash
   python -c "from orchestrator.pricing import calculate_cost; print(calculate_cost('gigachat', 'GigaChat', 1000))"
   # Expected output: 1.0 (₽1.00 for 1000 tokens)
   ```

3. Check logs for "Unknown provider" warnings

### Issue: Prometheus server fails to start

**Symptoms:**
```
❌ Failed to start server: [Errno 48] Address already in use
```

**Solutions:**
1. Port 9091 might be in use by another process
2. Try different port in code:
   ```python
   await router.start_metrics_server(port=9092)  # or 9093, etc.
   ```

3. Check what's using the port (Linux/Mac):
   ```bash
   lsof -i :9091
   ```

4. Check what's using the port (Windows):
   ```powershell
   netstat -ano | findstr :9091
   ```

### Issue: Test skipped due to missing credentials

**Symptoms:**
```
⚠️  GIGACHAT_API_KEY not found, skipping test
```

**Solution:**
1. Create `.env` file in project root (if it doesn't exist)
2. Add missing credentials:
   ```env
   GIGACHAT_API_KEY=your_api_key_here
   YANDEXGPT_API_KEY=your_iam_token_here
   YANDEXGPT_FOLDER_ID=your_folder_id_here
   ```
3. Verify `.env` is loaded:
   ```bash
   python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GIGACHAT_API_KEY'))"
   ```

### Issue: SSL certificate errors (GigaChat)

**Symptoms:**
```
❌ Test failed: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:**
This is normal for GigaChat with Russian CA certificates. The test already includes `verify_ssl=False` in the configuration, so this error shouldn't appear. If it does:

1. Check that `verify_ssl=False` is set in the config
2. Update `urllib3` and `httpx`:
   ```bash
   pip install --upgrade httpx urllib3
   ```

## Additional Notes

### Pricing Information

v0.7.0 uses fixed pricing from `src/orchestrator/pricing.py`:

| Provider | Model | Price (₽/1k tokens) |
|----------|-------|---------------------|
| GigaChat | GigaChat | 1.00 |
| GigaChat | GigaChat-Pro | 2.00 |
| GigaChat | GigaChat-Plus | 1.50 |
| YandexGPT | yandexgpt/latest | 1.50 |
| YandexGPT | yandexgpt-lite/latest | 0.75 |
| Ollama | (all models) | 0.00 (free) |
| Mock | (all models) | 0.00 (free) |

### Tokenization

- **Primary**: Uses `tiktoken` (v0.12.0+) for accurate GPT-like tokenization
- **Fallback**: Word-based estimation `len(text.split()) * 1.3` if tiktoken unavailable
- **Models**: Automatically selects encoding based on provider's model name

### Performance Expectations

Typical test execution time:
- Test 1 (GigaChat): ~3-5 seconds
- Test 2 (YandexGPT): ~3-5 seconds
- Test 3 (Streaming): ~4-6 seconds
- Test 4 (Prometheus): ~12-14 seconds (includes 10s manual verification window)

**Total**: ~25-30 seconds

## Contributing

Found a bug in v0.7.0 observability features? Please:
1. Run this test suite to reproduce the issue
2. Include test output in your bug report
3. Open an issue on GitHub with details

## Version History

- **v0.7.0** (December 13, 2025): Initial observability release
  - Token tracking
  - Cost estimation
  - Prometheus integration

