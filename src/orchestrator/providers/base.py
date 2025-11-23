"""Base provider interface for LLM implementations.

This module provides the foundational abstractions for all LLM provider
integrations in the Multi-LLM Orchestrator. It includes configuration models,
exception hierarchy, and the abstract base class that all providers must implement.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# CONFIGURATION MODELS
# ============================================================================


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider.

    This model defines all necessary configuration parameters for initializing
    and managing a connection to an LLM provider service.

    Attributes:
        name: Unique identifier for the provider instance
        api_key: Authentication key for the provider API (optional for local providers)
        base_url: Base URL for the provider's API endpoints (optional if provider has default)
        timeout: Maximum time in seconds to wait for API responses (1-300 seconds)
        max_retries: Maximum number of retry attempts for failed requests (0-10)
        model: Specific model name or version to use (optional, provider-specific)
        scope: OAuth2 scope for providers that require it (optional, provider-specific)

    Example:
        ```python
        config = ProviderConfig(
            name="gigachat-prod",
            api_key="your_api_key_here",
            base_url="https://gigachat.devices.sberbank.ru/api/v1",
            timeout=60,
            max_retries=3,
            model="GigaChat-2-Pro"
        )
        ```
    """

    name: str = Field(
        ...,
        description="Provider identifier (e.g., 'gigachat', 'yandexgpt')"
    )
    api_key: str | None = Field(
        None,
        description="API authentication key"
    )
    base_url: str | None = Field(
        None,
        description="Base URL for API endpoints"
    )
    timeout: int = Field(
        30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests"
    )
    model: str | None = Field(
        None,
        description="Model name or version (e.g., 'GigaChat-2-Pro', 'yandexgpt-lite')"
    )
    scope: str | None = Field(
        None,
        description="OAuth2 scope for providers that require it (e.g., 'GIGACHAT_API_PERS', 'GIGACHAT_API_CORP')"
    )


class GenerationParams(BaseModel):
    """Parameters for controlling text generation behavior.

    These parameters allow fine-tuning the output characteristics of LLM
    text generation requests.

    Attributes:
        temperature: Controls randomness in generation (0.0 = deterministic, 2.0 = very random)
        max_tokens: Maximum number of tokens to generate in the response
        top_p: Nucleus sampling parameter - considers tokens with cumulative probability up to top_p
        stop: List of sequences that will stop generation when encountered

    Example:
        ```python
        params = GenerationParams(
            temperature=0.8,
            max_tokens=2000,
            top_p=0.95,
            stop=["\\n\\n", "END"]
        )
        ```
    """

    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for randomness control"
    )
    max_tokens: int = Field(
        1000,
        ge=1,
        description="Maximum tokens to generate"
    )
    top_p: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability threshold"
    )
    stop: list[str] | None = Field(
        None,
        description="Stop sequences for generation termination"
    )


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class ProviderError(Exception):
    """Base exception for all provider-related errors.

    All provider-specific exceptions inherit from this base class,
    allowing for unified error handling across different provider implementations.

    Example:
        ```python
        try:
            response = await provider.generate("Hello")
        except ProviderError as e:
            logger.error(f"Provider error occurred: {e}")
        ```
    """

    pass


class AuthenticationError(ProviderError):
    """Raised when authentication with the provider fails.

    This typically corresponds to HTTP 401 Unauthorized responses,
    indicating invalid or expired API credentials.

    Example:
        ```python
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        ```
    """

    pass


class RateLimitError(ProviderError):
    """Raised when the provider's rate limit is exceeded.

    This corresponds to HTTP 429 Too Many Requests responses.
    The request should be retried after a delay.

    Example:
        ```python
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded, retry after delay")
        ```
    """

    pass


class TimeoutError(ProviderError):
    """Raised when a request to the provider times out.

    This occurs when the provider doesn't respond within the
    configured timeout period.

    Example:
        ```python
        try:
            response = await asyncio.wait_for(request(), timeout=30)
        except asyncio.TimeoutError:
            raise TimeoutError("Request timed out after 30 seconds")
        ```
    """

    pass


class InvalidRequestError(ProviderError):
    """Raised when the request to the provider is invalid.

    This typically corresponds to HTTP 400 Bad Request responses,
    indicating malformed requests or invalid parameters.

    Example:
        ```python
        if response.status_code == 400:
            raise InvalidRequestError("Invalid request parameters")
        ```
    """

    pass


# ============================================================================
# PROVIDER BASE CLASS
# ============================================================================


class BaseProvider(ABC):
    """Abstract base class for all LLM providers.

    This class defines the interface that all LLM provider implementations
    must follow. It provides concrete implementations for common functionality
    like retry logic and metadata retrieval, while requiring providers to
    implement their own generation and health check logic.

    Subclasses must implement:
        - generate(): Text generation from prompts
        - health_check(): Provider availability verification

    Attributes:
        config: Provider configuration settings
        logger: Logger instance for this provider

    Example:
        ```python
        class MyProvider(BaseProvider):
            async def generate(self, prompt: str, params: Optional[GenerationParams] = None) -> str:
                # Custom implementation
                response = await self._make_api_request(prompt, params)
                return response.text

            async def health_check(self) -> bool:
                try:
                    await self._ping_endpoint()
                    return True
                except Exception:
                    return False

        # Usage
        config = ProviderConfig(name="my-provider", api_key="key123")
        provider = MyProvider(config)
        response = await provider.generate("Hello, world!")
        ```
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the provider with configuration.

        Args:
            config: Provider configuration containing API credentials,
                   timeouts, retry settings, and other provider-specific options
        """
        self.config = config
        self.logger = logging.getLogger(f"orchestrator.providers.{config.name}")
        self.logger.info(f"Initialized provider: {config.name}")

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None
    ) -> str:
        """Generate text completion from a prompt.

        This is the primary method for interacting with an LLM provider.
        It takes a text prompt and optional generation parameters, and
        returns the generated text response.

        Args:
            prompt: Input text prompt to generate completion for
            params: Optional generation parameters (temperature, max_tokens, etc.)
                   If None, provider defaults will be used

        Returns:
            Generated text response from the LLM

        Raises:
            AuthenticationError: If API authentication fails
            RateLimitError: If provider rate limit is exceeded
            TimeoutError: If request times out
            InvalidRequestError: If request parameters are invalid
            ProviderError: For other provider-specific errors

        Example:
            ```python
            # Simple generation
            response = await provider.generate("What is Python?")

            # With custom parameters
            params = GenerationParams(temperature=0.9, max_tokens=500)
            response = await provider.generate("Write a poem", params=params)
            ```
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and available.

        This method should verify that the provider's API is accessible
        and responding correctly. The specific implementation depends on
        the provider (e.g., ping endpoint, test request, etc.).

        Returns:
            True if provider is healthy and available, False otherwise

        Example:
            ```python
            if await provider.health_check():
                response = await provider.generate("Hello")
            else:
                logger.error("Provider is unhealthy")
            ```
        """
        pass

    def get_model_info(self) -> dict[str, Any]:
        """Get provider and model metadata.

        Returns a dictionary containing information about the provider
        instance, including its name, configured model, and type.

        Returns:
            Dictionary with provider metadata:
                - name: Provider instance name
                - model: Configured model name (if any)
                - provider_type: Python class name of the provider

        Example:
            ```python
            info = provider.get_model_info()
            # {'name': 'gigachat-prod', 'model': 'GigaChat-2-Pro', 'provider_type': 'GigaChatProvider'}
            ```
        """
        return {
            "name": self.config.name,
            "model": self.config.model,
            "provider_type": self.__class__.__name__
        }

    async def _retry_with_backoff(
        self,
        func: Callable[[], Any],
        max_retries: int | None = None
    ) -> Any:
        """Retry an async function with exponential backoff.

        This method implements a retry mechanism with exponential backoff
        for handling transient failures like rate limits and timeouts.
        The wait time between retries increases exponentially: 1s, 2s, 4s, 8s, etc.,
        capped at 30 seconds.

        Only RateLimitError and TimeoutError are retried automatically.
        Other exceptions are raised immediately.

        Args:
            func: Async callable to retry (must be a no-argument function)
            max_retries: Maximum number of retry attempts. If None, uses
                        the value from provider config (default: 3)

        Returns:
            The return value from a successful function call

        Raises:
            RateLimitError: If all retry attempts are exhausted due to rate limiting
            TimeoutError: If all retry attempts are exhausted due to timeouts

        Example:
            ```python
            async def make_request():
                response = await httpx.get(url, timeout=self.config.timeout)
                if response.status_code == 429:
                    raise RateLimitError("Rate limited")
                return response.json()

            # Will retry up to 3 times with exponential backoff
            result = await self._retry_with_backoff(make_request)
            ```
        """
        max_retries = max_retries or self.config.max_retries

        for attempt in range(max_retries):
            try:
                return await func()
            except (RateLimitError, TimeoutError) as e:
                # If this was the last attempt, raise the error
                if attempt == max_retries - 1:
                    self.logger.error(
                        f"Max retries ({max_retries}) reached for {self.config.name}: {e}"
                    )
                    raise

                # Calculate exponential backoff with cap at 30 seconds
                wait_time = min(2 ** attempt, 30)
                self.logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed for {self.config.name}: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
