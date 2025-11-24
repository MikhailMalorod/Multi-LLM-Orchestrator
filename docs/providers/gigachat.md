# GigaChat Provider

GigaChatProvider provides integration with GigaChat (Sber) API, a Russian LLM service.

## Overview

GigaChat is a large language model developed by Sber (Sberbank). The provider supports OAuth2 authentication with automatic token refresh, full parameter support, and comprehensive error handling.

## Authentication

GigaChat uses OAuth2 authentication:

1. **Authorization Key**: Obtain from [GigaChat Developer Portal](https://developers.sber.ru/)
2. **OAuth2 Scope**: 
   - `GIGACHAT_API_PERS` - Personal use
   - `GIGACHAT_API_CORP` - Corporate use
3. **Automatic Token Refresh**: The provider automatically refreshes access tokens before expiration (30-minute validity)

## Configuration

```python
from orchestrator.providers import ProviderConfig, GigaChatProvider

config = ProviderConfig(
    name="gigachat",
    api_key="your_authorization_key_here",  # OAuth2 authorization key
    scope="GIGACHAT_API_PERS",  # or "GIGACHAT_API_CORP"
    model="GigaChat",  # or "GigaChat-Pro", "GigaChat-Plus"
    timeout=30.0,
    verify_ssl=False  # Required for Russian CA certificates
)
```

**Important:** GigaChat uses Russian CA certificates. You must set `verify_ssl=False` in development, or install Russian CA certificates in production.

⚠️ **Security Warning:** Disabling SSL verification is insecure. Use only in development or with trusted networks.

## Supported Parameters

- **temperature**: Controls randomness (0.0-2.0)
- **max_tokens**: Maximum tokens to generate
- **top_p**: Nucleus sampling parameter
- **stop**: List of stop sequences

## Usage

### Basic Usage

```python
import asyncio
from orchestrator.providers import ProviderConfig, GigaChatProvider

async def main():
    config = ProviderConfig(
        name="gigachat",
        api_key="your_authorization_key_here",
        scope="GIGACHAT_API_PERS",
        model="GigaChat",
        verify_ssl=False
    )
    provider = GigaChatProvider(config)
    
    response = await provider.generate("What is Python?")
    print(response)

asyncio.run(main())
```

### With Router

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, GigaChatProvider

async def main():
    router = Router(strategy="round-robin")
    
    config = ProviderConfig(
        name="gigachat",
        api_key="your_authorization_key_here",
        scope="GIGACHAT_API_PERS",
        model="GigaChat",
        verify_ssl=False
    )
    router.add_provider(GigaChatProvider(config))
    
    response = await router.route("What is Python?")
    print(response)

asyncio.run(main())
```

### With Custom Parameters

```python
from orchestrator.providers.base import GenerationParams

params = GenerationParams(
    temperature=0.8,
    max_tokens=500,
    top_p=0.95
)
response = await provider.generate("Write a poem", params=params)
```

### Health Check

```python
is_healthy = await provider.health_check()
if is_healthy:
    response = await provider.generate("Hello")
```

## Models

Supported models:
- `GigaChat` - Standard model
- `GigaChat-Pro` - Pro version
- `GigaChat-Plus` - Plus version

## Error Handling

The provider maps HTTP errors to custom exceptions:

- **401 Unauthorized** → `AuthenticationError`
- **429 Too Many Requests** → `RateLimitError`
- **Timeout** → `TimeoutError`
- **400 Bad Request** → `InvalidRequestError`

All exceptions inherit from `ProviderError`.

## OAuth2 Token Management

The provider automatically manages OAuth2 tokens:

1. **Initial Token**: Obtained on first request using authorization key
2. **Token Refresh**: Automatically refreshed 60 seconds before expiration
3. **Thread Safety**: Token updates are thread-safe using async locks
4. **Error Recovery**: If token expires during request (401), it's refreshed and request is retried

## See Also

- [GigaChatProvider Implementation](../../src/orchestrator/providers/gigachat.py)
- [Creating Custom Provider](custom_provider.md)
- [Architecture Overview](../architecture.md)

