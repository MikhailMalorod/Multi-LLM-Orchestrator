# YandexGPT Provider

YandexGPTProvider provides integration with YandexGPT (Yandex Cloud) API, a Russian LLM service.

## Overview

YandexGPT is a large language model service provided by Yandex Cloud. The provider supports IAM token authentication, full parameter support, and comprehensive error handling.

## Authentication

YandexGPT uses IAM token authentication:

1. **IAM Token**: Obtain from Yandex Cloud Console
2. **Token Validity**: 12 hours (user-managed)
3. **Folder ID**: Required Yandex Cloud folder ID

**Note:** Unlike GigaChat, YandexGPT does not support automatic token refresh. You must manually refresh the IAM token before it expires.

## Configuration

```python
from orchestrator.providers import ProviderConfig, YandexGPTProvider

config = ProviderConfig(
    name="yandexgpt",
    api_key="your_iam_token_here",  # IAM token (valid for 12 hours)
    folder_id="your_folder_id_here",  # Yandex Cloud folder ID
    model="yandexgpt/latest",  # or "yandexgpt-lite/latest"
    timeout=30.0
)
```

## Supported Parameters

- **temperature**: Controls randomness (0.0-2.0)
- **max_tokens**: Maximum tokens to generate (mapped to `maxTokens` in API)

**Note:** YandexGPT API does not support `top_p` or `stop` parameters.

## Usage

### Basic Usage

```python
import asyncio
from orchestrator.providers import ProviderConfig, YandexGPTProvider

async def main():
    config = ProviderConfig(
        name="yandexgpt",
        api_key="your_iam_token_here",
        folder_id="your_folder_id_here",
        model="yandexgpt/latest"
    )
    provider = YandexGPTProvider(config)
    
    response = await provider.generate("What is Python?")
    print(response)

asyncio.run(main())
```

### With Router

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, YandexGPTProvider

async def main():
    router = Router(strategy="round-robin")
    
    config = ProviderConfig(
        name="yandexgpt",
        api_key="your_iam_token_here",
        folder_id="your_folder_id_here",
        model="yandexgpt/latest"
    )
    router.add_provider(YandexGPTProvider(config))
    
    response = await router.route("What is Python?")
    print(response)

asyncio.run(main())
```

### With Custom Parameters

```python
from orchestrator.providers.base import GenerationParams

params = GenerationParams(
    temperature=0.8,
    max_tokens=500
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
- `yandexgpt/latest` - Full-featured model
- `yandexgpt-lite/latest` - Lightweight model (faster, lower cost)

## Error Handling

The provider maps HTTP errors to custom exceptions:

- **401 Unauthorized** → `AuthenticationError` (token expired or invalid)
- **429 Too Many Requests** → `RateLimitError`
- **Timeout** → `TimeoutError`
- **400 Bad Request** → `InvalidRequestError`

All exceptions inherit from `ProviderError`.

## IAM Token Management

**Important:** YandexGPT does not support automatic token refresh. You must:

1. **Obtain IAM Token**: Use Yandex Cloud CLI or API
2. **Monitor Expiration**: Token is valid for 12 hours
3. **Refresh Before Expiration**: Update `config.api_key` with new token
4. **Handle 401 Errors**: Catch `AuthenticationError` and refresh token

Example token refresh:

```python
from orchestrator.providers.base import AuthenticationError

try:
    response = await provider.generate("Hello")
except AuthenticationError:
    # Token expired, refresh it
    new_token = get_new_iam_token()  # Your token refresh logic
    provider.config.api_key = new_token
    response = await provider.generate("Hello")
```

## See Also

- [YandexGPTProvider Implementation](../../src/orchestrator/providers/yandexgpt.py)
- [Creating Custom Provider](custom_provider.md)
- [Architecture Overview](../architecture.md)

