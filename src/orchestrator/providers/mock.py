"""Mock provider implementation for testing and development.

This module provides a MockProvider class that simulates LLM provider behavior
without making actual API calls. It supports various simulation modes including
normal responses, timeouts, rate limits, and authentication errors.

The MockProvider is useful for:
    - Unit testing router and orchestration logic
    - Development without API credentials
    - Simulating error conditions and edge cases
    - Performance testing with controlled response times
"""

import asyncio

from .base import (
    AuthenticationError,
    BaseProvider,
    GenerationParams,
    InvalidRequestError,
    ProviderConfig,
    RateLimitError,
    TimeoutError,
)

# ============================================================================
# MOCK PROVIDER
# ============================================================================


class MockProvider(BaseProvider):
    """Mock LLM provider for testing and development.

    This provider simulates LLM behavior without making actual API calls.
    It supports multiple simulation modes controlled via the `config.model` field:

    Modes:
        - "mock-normal" (default): Returns a mock response with 0.1s delay
        - "mock-timeout": Raises TimeoutError immediately
        - "mock-ratelimit": Raises RateLimitError immediately
        - "mock-auth-error": Raises AuthenticationError immediately
        - "mock-invalid-request": Raises InvalidRequestError immediately
        - Any mode containing "unhealthy": health_check() returns False

    The provider respects GenerationParams.max_tokens (interpreted as character
    limit) and ignores other generation parameters.

    Attributes:
        config: Provider configuration. If config.model is not specified,
               defaults to "mock-normal" mode.

    Example:
        ```python
        # Normal mode
        config = ProviderConfig(name="mock", model="mock-normal")
        provider = MockProvider(config)
        response = await provider.generate("Hello, world!")
        # Returns: "Mock response to: Hello, world!"

        # Timeout simulation
        config = ProviderConfig(name="mock", model="mock-timeout")
        provider = MockProvider(config)
        try:
            await provider.generate("Test")
        except TimeoutError:
            print("Timeout simulated")

        # Rate limit simulation
        config = ProviderConfig(name="mock", model="mock-ratelimit")
        provider = MockProvider(config)
        try:
            await provider.generate("Test")
        except RateLimitError:
            print("Rate limit simulated")

        # Unhealthy provider
        config = ProviderConfig(name="mock", model="mock-unhealthy")
        provider = MockProvider(config)
        is_healthy = await provider.health_check()
        # Returns: False
        ```
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the mock provider with configuration.

        Args:
            config: Provider configuration. If config.model is not specified,
                   defaults to "mock-normal" mode.
        """
        super().__init__(config)
        actual_mode = config.model or "mock-normal"
        self.logger.info(f"MockProvider initialized in mode: {actual_mode}")

    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None
    ) -> str:
        """Generate mock text completion from a prompt.

        This method simulates LLM text generation based on the configured mode.
        In normal mode, it returns a mock response with a small delay. In error
        modes, it immediately raises the corresponding exception.

        Args:
            prompt: Input text prompt to generate completion for
            params: Optional generation parameters. Only max_tokens is respected
                   (interpreted as character limit). Other parameters are ignored.

        Returns:
            Generated mock text response. Format: "Mock response to: {prompt}"
            Truncated to max_tokens characters if specified.

        Raises:
            TimeoutError: If mode is "mock-timeout"
            RateLimitError: If mode is "mock-ratelimit"
            AuthenticationError: If mode is "mock-auth-error"
            InvalidRequestError: If mode is "mock-invalid-request"

        Example:
            ```python
            # Normal generation
            config = ProviderConfig(name="mock", model="mock-normal")
            provider = MockProvider(config)
            response = await provider.generate("Hello")
            # Returns: "Mock response to: Hello"

            # With max_tokens limit
            params = GenerationParams(max_tokens=10)
            response = await provider.generate("Very long prompt", params=params)
            # Returns: "Mock respon" (truncated to 10 characters)

            # Timeout simulation
            config = ProviderConfig(name="mock", model="mock-timeout")
            provider = MockProvider(config)
            try:
                await provider.generate("Test")
            except TimeoutError as e:
                print(f"Timeout: {e}")
            ```

        Note:
            max_tokens is interpreted as character limit for mock responses.
            The method uses case-insensitive mode matching.
        """
        # Determine mode (case-insensitive, default to "mock-normal")
        mode = (self.config.model or "mock-normal").lower()

        # Handle error simulation modes
        if mode == "mock-timeout":
            raise TimeoutError("Mock timeout simulation")
        elif mode == "mock-ratelimit":
            raise RateLimitError("Mock rate limit simulation")
        elif mode == "mock-auth-error":
            raise AuthenticationError("Mock authentication failure")
        elif mode == "mock-invalid-request":
            raise InvalidRequestError("Mock invalid request")

        # Normal mode: generate mock response with delay
        await asyncio.sleep(0.1)
        response = f"Mock response to: {prompt}"

        # Apply max_tokens limit if specified (interpreted as character limit)
        if params and params.max_tokens:
            response = response[:params.max_tokens]

        self.logger.debug(f"Generating mock response for prompt: {prompt[:50]}...")
        return response

    async def health_check(self) -> bool:
        """Check if the mock provider is healthy and available.

        This method simulates provider health status. If the configured mode
        contains "unhealthy" (case-insensitive), it returns False. Otherwise,
        it returns True.

        Returns:
            True if provider is healthy, False if mode contains "unhealthy"

        Example:
            ```python
            # Healthy provider
            config = ProviderConfig(name="mock", model="mock-normal")
            provider = MockProvider(config)
            is_healthy = await provider.health_check()
            # Returns: True

            # Unhealthy provider
            config = ProviderConfig(name="mock", model="mock-unhealthy")
            provider = MockProvider(config)
            is_healthy = await provider.health_check()
            # Returns: False

            # Partial match also works
            config = ProviderConfig(name="mock", model="mock-normal-unhealthy")
            provider = MockProvider(config)
            is_healthy = await provider.health_check()
            # Returns: False
            ```
        """
        # Check if "unhealthy" is present in mode (case-insensitive, partial match)
        if "unhealthy" in (self.config.model or "").lower():
            return False
        return True

