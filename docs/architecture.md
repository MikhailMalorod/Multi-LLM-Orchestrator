# Architecture Overview

This document provides an overview of the Multi-LLM Orchestrator architecture, its components, and how they work together.

## Components

### Router

The `Router` is the central component that manages provider selection and request routing. It implements intelligent routing strategies and automatic fallback mechanisms.

**Key Features:**
- Multiple routing strategies (round-robin, random, first-available)
- Automatic fallback when providers fail
- Provider health checking
- Request logging and error handling

**Location:** `src/orchestrator/router.py`

**Example:**
```python
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider

router = Router(strategy="round-robin")
config = ProviderConfig(name="provider1", model="mock-normal")
router.add_provider(MockProvider(config))

response = await router.route("Hello, world!")
```

### BaseProvider

`BaseProvider` is an abstract base class that defines the interface all LLM providers must implement. It provides common functionality like retry logic with exponential backoff and metadata retrieval.

**Required Methods:**
- `generate(prompt: str, params: GenerationParams | None) -> str`: Generate text completion
- `health_check() -> bool`: Check if provider is available

**Common Functionality:**
- Retry logic with exponential backoff (for RateLimitError and TimeoutError)
- Provider metadata via `get_model_info()`
- Logging integration

**Location:** `src/orchestrator/providers/base.py`

**Example:**
```python
from orchestrator.providers.base import BaseProvider, ProviderConfig

class MyProvider(BaseProvider):
    async def generate(self, prompt: str, params=None):
        # Custom implementation
        return "Response"
    
    async def health_check(self):
        # Check provider availability
        return True
```

### ProviderConfig

`ProviderConfig` is a Pydantic model that defines all configuration parameters for a provider instance.

**Key Fields:**
- `name`: Unique identifier for the provider
- `api_key`: Authentication key (optional for local providers)
- `base_url`: API endpoint URL (optional if provider has default)
- `timeout`: Request timeout in seconds (1-300, default: 30)
- `max_retries`: Maximum retry attempts (0-10, default: 3)
- `verify_ssl`: Enable SSL certificate verification (default: True)
- `model`: Model name or version (provider-specific)
- `scope`: OAuth2 scope (for providers that require it)
- `folder_id`: Yandex Cloud folder ID (for YandexGPT)

**Location:** `src/orchestrator/providers/base.py`

### GenerationParams

`GenerationParams` is a Pydantic model that controls text generation behavior.

**Key Fields:**
- `temperature`: Randomness control (0.0-2.0, default: 0.7)
- `max_tokens`: Maximum tokens to generate (default: 1000)
- `top_p`: Nucleus sampling parameter (0.0-1.0, default: 1.0)
- `stop`: List of stop sequences (optional)

**Location:** `src/orchestrator/providers/base.py`

## Request Flow

Here's how a request flows through the system:

1. **User calls `router.route(prompt, params)`**
   - Router validates that providers are registered
   - Router selects a provider based on the configured strategy

2. **Provider Selection**
   - **round-robin**: Cycles through providers in order
   - **random**: Selects a random provider
   - **first-available**: Selects the first healthy provider (via health_check)

3. **Request Execution**
   - Router calls `provider.generate(prompt, params)`
   - Provider makes API request (or simulates it for MockProvider)
   - Provider handles retries with exponential backoff if needed

4. **Fallback Mechanism**
   - If a provider fails, Router automatically tries the next provider
   - Continues until a provider succeeds or all providers fail
   - Raises the last exception if all providers fail

5. **Response Return**
   - Successful response is returned to the user
   - Router logs the successful provider for debugging

## Routing Strategies

### round-robin

Cycles through providers in a fixed order. Best for equal load distribution across providers.

```python
router = Router(strategy="round-robin")
# Request 1 → Provider A
# Request 2 → Provider B
# Request 3 → Provider C
# Request 4 → Provider A (cycle repeats)
```

### random

Selects a random provider from available providers. Useful for simple load balancing.

```python
router = Router(strategy="random")
# Each request randomly selects from available providers
```

### first-available

Selects the first healthy provider based on health checks. Best for high availability scenarios.

```python
router = Router(strategy="first-available")
# Checks providers in order, selects first healthy one
# Falls back to trying all providers if none are healthy
```

## Exception Hierarchy

All provider-related exceptions inherit from `ProviderError`:

```
ProviderError (base exception)
├── AuthenticationError (401 Unauthorized)
├── RateLimitError (429 Too Many Requests)
├── TimeoutError (request timeout)
└── InvalidRequestError (400 Bad Request)
```

**Location:** `src/orchestrator/providers/base.py`

**Usage:**
```python
from orchestrator.providers.base import ProviderError, AuthenticationError

try:
    response = await provider.generate("Hello")
except AuthenticationError:
    # Handle authentication failure
    pass
except ProviderError:
    # Handle other provider errors
    pass
```

## Implementation Details

### Retry Logic

Providers automatically retry failed requests with exponential backoff:
- Only `RateLimitError` and `TimeoutError` are retried
- Backoff: 1s, 2s, 4s, 8s, ... (capped at 30s)
- Maximum retries: configurable via `ProviderConfig.max_retries` (default: 3)

### Health Checks

Health checks verify provider availability:
- `first-available` strategy uses health checks to skip unhealthy providers
- Health check implementation is provider-specific
- GigaChat: Validates OAuth2 token
- YandexGPT: Makes minimal API request
- MockProvider: Returns False for "unhealthy" modes

### Logging

All components use Python's `logging` module:
- Router: `orchestrator.router`
- Providers: `orchestrator.providers.{provider_name}`
- Log level can be configured via environment variables

## See Also

- [Router Implementation](src/orchestrator/router.py)
- [BaseProvider Implementation](src/orchestrator/providers/base.py)
- [Provider Documentation](providers/)
- [Contributing Guide](../CONTRIBUTING.md)

