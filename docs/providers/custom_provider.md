# Creating Custom Provider

This guide explains how to create a custom LLM provider for Multi-LLM Orchestrator.

## Requirements

To create a custom provider, you must:

1. Inherit from `BaseProvider`
2. Implement `generate()` method
3. Implement `health_check()` method
4. Handle exceptions properly
5. Add comprehensive tests

## Step-by-Step Guide

### Step 1: Create Provider Class

Create a new file `src/orchestrator/providers/your_provider.py`:

```python
"""Your provider implementation for Multi-LLM Orchestrator."""

from typing import Any

import httpx

from .base import (
    AuthenticationError,
    BaseProvider,
    GenerationParams,
    InvalidRequestError,
    ProviderConfig,
    ProviderError,
    RateLimitError,
    TimeoutError,
)


class YourProvider(BaseProvider):
    """Your custom LLM provider implementation."""
    
    # API constants (if applicable)
    DEFAULT_BASE_URL: str = "https://api.example.com/v1"
    DEFAULT_MODEL: str = "your-model"
    
    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__(config)
        # Set default base_url if not provided
        if not self.config.base_url:
            self.config.base_url = self.DEFAULT_BASE_URL
        
        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            verify=self.config.verify_ssl
        )
    
    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None
    ) -> str:
        """Generate text completion from a prompt.
        
        Args:
            prompt: Input text prompt
            params: Optional generation parameters
            
        Returns:
            Generated text response
            
        Raises:
            AuthenticationError: If API authentication fails
            RateLimitError: If rate limit is exceeded
            TimeoutError: If request times out
            InvalidRequestError: If request is invalid
            ProviderError: For other provider-specific errors
        """
        # Prepare request
        url = f"{self.config.base_url}/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        # Map GenerationParams to API format
        payload = {
            "prompt": prompt,
            "model": self.config.model or self.DEFAULT_MODEL,
        }
        
        if params:
            payload["temperature"] = params.temperature
            payload["max_tokens"] = params.max_tokens
            # Add other parameters as needed
        
        # Make request with retry logic
        async def make_request() -> str:
            response = await self._client.post(url, json=payload, headers=headers)
            
            # Handle errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status_code == 400:
                raise InvalidRequestError("Invalid request parameters")
            elif response.status_code != 200:
                raise ProviderError(f"API error: {response.status_code}")
            
            # Parse response
            data = response.json()
            return data["text"]  # Adjust based on your API response format
        
        # Use retry logic from BaseProvider
        return await self._retry_with_backoff(make_request)
    
    async def health_check(self) -> bool:
        """Check if the provider is healthy and available.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Make a minimal request to check availability
            url = f"{self.config.base_url}/health"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}"
            }
            response = await self._client.get(url, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()
```

### Step 2: Register Provider

Add your provider to `src/orchestrator/providers/__init__.py`:

```python
from .your_provider import YourProvider

__all__ = [
    # ... existing providers
    "YourProvider",
]
```

### Step 3: Add to Router

Use your provider with Router:

```python
from orchestrator import Router
from orchestrator.providers import ProviderConfig, YourProvider

router = Router(strategy="round-robin")

config = ProviderConfig(
    name="your-provider",
    api_key="your_api_key",
    model="your-model"
)
router.add_provider(YourProvider(config))

response = await router.route("Hello, world!")
```

### Step 4: Write Tests

Create `tests/test_your_provider.py`:

```python
import pytest
from orchestrator.providers import ProviderConfig, YourProvider
from orchestrator.providers.base import (
    AuthenticationError,
    RateLimitError,
    TimeoutError,
)

@pytest.mark.asyncio
async def test_generate_success():
    """Test successful generation."""
    config = ProviderConfig(
        name="test",
        api_key="test_key",
        model="test-model"
    )
    provider = YourProvider(config)
    
    # Mock HTTP client or use test API
    response = await provider.generate("Hello")
    assert isinstance(response, str)

@pytest.mark.asyncio
async def test_health_check():
    """Test health check."""
    config = ProviderConfig(name="test", api_key="test_key")
    provider = YourProvider(config)
    
    is_healthy = await provider.health_check()
    assert isinstance(is_healthy, bool)
```

## Best Practices

### 1. Error Handling

Always map HTTP errors to appropriate exceptions:

```python
if response.status_code == 401:
    raise AuthenticationError("Invalid credentials")
elif response.status_code == 429:
    raise RateLimitError("Rate limit exceeded")
```

### 2. Use Retry Logic

Leverage `_retry_with_backoff()` from BaseProvider:

```python
async def make_request():
    # Your request logic
    pass

result = await self._retry_with_backoff(make_request)
```

### 3. Logging

Use the logger from BaseProvider:

```python
self.logger.info("Making request to API")
self.logger.warning("Rate limit approaching")
self.logger.error("Request failed")
```

### 4. Configuration

Use `ProviderConfig` for all configuration:

```python
# Good
config = ProviderConfig(
    name="provider",
    api_key="key",
    timeout=60,
    max_retries=5
)

# Bad - don't add custom fields
config.custom_field = "value"  # Won't work with Pydantic
```

### 5. Type Hints

Always use type hints:

```python
async def generate(
    self,
    prompt: str,
    params: GenerationParams | None = None
) -> str:
    ...
```

## Testing

### Unit Tests

Test provider logic without making real API calls:

```python
@pytest.mark.asyncio
async def test_generate_with_mock():
    """Test with mocked HTTP client."""
    # Mock httpx.AsyncClient
    ...
```

### Integration Tests

Test with real API (if available):

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_real():
    """Test with real API."""
    config = ProviderConfig(
        name="test",
        api_key=os.getenv("TEST_API_KEY")
    )
    provider = YourProvider(config)
    response = await provider.generate("Hello")
    assert response
```

## Documentation

Create documentation in `docs/providers/your_provider.md`:

```markdown
# Your Provider

Brief description of your provider.

## Authentication
How to obtain API keys.

## Configuration
Example configuration.

## Usage
Code examples.

## See Also
- [YourProvider Implementation](../../src/orchestrator/providers/your_provider.py)
```

## Contributing

After implementing your provider:

1. Add comprehensive tests (coverage >= 87%)
2. Update documentation
3. Ensure type checking passes (`mypy src/ --strict`)
4. Ensure linting passes (`ruff check src/`)
5. Submit a Pull Request

## See Also

- [BaseProvider Implementation](../../src/orchestrator/providers/base.py)
- [GigaChatProvider Example](../../src/orchestrator/providers/gigachat.py)
- [YandexGPTProvider Example](../../src/orchestrator/providers/yandexgpt.py)
- [Architecture Overview](../architecture.md)
- [Contributing Guide](../../CONTRIBUTING.md)

