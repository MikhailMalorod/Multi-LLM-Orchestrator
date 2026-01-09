## 🎉 Usage Tracking Callbacks

Add comprehensive usage tracking for billing and analytics integration.

### ✨ New Features

- **Python callback** support via `usage_callback` parameter
- **HTTP POST callback** support via `callback_url` parameter
- Optional **tenant_id** and **platform_key_id** context fields
- Comprehensive **UsageData** with tokens, cost, latency, success status
- **Fail-silent** behavior: callback errors don't disrupt requests
- Full **streaming** support (`route()` and `route_stream()`)
- Complete **fallback** support: callback invoked for each provider attempt

### 📚 Examples

#### Python Callback
```python
from orchestrator import Router, UsageData

async def track_usage(data: UsageData) -> None:
    await billing_api.record(data.cost, data.total_tokens)

router = Router(usage_callback=track_usage)
```

#### HTTP POST Callback (Platform SaaS)
```python
router = Router(
    callback_url="https://api.example.com/usage",
    tenant_id="tenant-123",
    platform_key_id="key-456",
)
```

### 📦 Installation

```bash
pip install --upgrade multi-llm-orchestrator
# or
pip install multi-llm-orchestrator==0.7.6
```

### 🔗 Links

- Closes [#7](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/issues/7)
- Pull Request: [#8](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/pull/8)
- Full documentation: [README - Usage Tracking](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator#usage-tracking)

### ⚙️ Backward Compatibility

✅ **Fully backward compatible** - all new parameters optional.

### 📊 Testing

- 241 tests passed (15 new tests for usage callbacks)
- 88% code coverage
- Ruff: 0 warnings
- Mypy: 0 errors (strict mode)

### 🙏 Thanks

Special thanks to Platform SaaS Team for the detailed requirements and use case analysis. Delivered 2 days ahead of schedule!

