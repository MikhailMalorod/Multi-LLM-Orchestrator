"""LLM Router module for managing provider selection and request routing."""

import logging
import random
from collections.abc import AsyncIterator

from .providers.base import BaseProvider, GenerationParams, ProviderError

# Valid routing strategies
VALID_STRATEGIES = ["round-robin", "random", "first-available"]


class Router:
    """Router for managing LLM provider selection and request routing.

    The Router handles intelligent routing of requests to appropriate
    LLM providers based on configurable routing strategies. It supports
    multiple routing strategies including round-robin, random selection,
    and first-available provider selection with automatic fallback.

    Attributes:
        strategy: Routing strategy to use for provider selection
        providers: List of registered provider instances
        _current_index: Current index for round-robin strategy (internal)
        logger: Logger instance for this router

    Example:
        ```python
        from orchestrator import Router
        from orchestrator.providers.base import ProviderConfig
        from orchestrator.providers.mock import MockProvider

        # Initialize router with round-robin strategy
        router = Router(strategy="round-robin")

        # Add providers
        config1 = ProviderConfig(name="provider1", model="mock-normal")
        provider1 = MockProvider(config1)
        router.add_provider(provider1)

        config2 = ProviderConfig(name="provider2", model="mock-normal")
        provider2 = MockProvider(config2)
        router.add_provider(provider2)

        # Route a request
        response = await router.route("Hello, world!")
        ```
    """

    def __init__(self, strategy: str = "round-robin") -> None:
        """Initialize the router with a routing strategy.

        Args:
            strategy: Routing strategy to use. Must be one of:
                - "round-robin": Select providers in a cyclic order
                - "random": Select a random provider from available providers
                - "first-available": Select the first healthy provider

        Raises:
            ValueError: If the provided strategy is not valid

        Example:
            ```python
            # Round-robin (default)
            router = Router()

            # Random selection
            router = Router(strategy="random")

            # First available healthy provider
            router = Router(strategy="first-available")
            ```
        """
        # Validate strategy
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy: {strategy}. "
                f"Must be one of {VALID_STRATEGIES}"
            )

        self.strategy = strategy
        self.providers: list[BaseProvider] = []
        self._current_index: int = 0
        self.logger = logging.getLogger("orchestrator.router")

        self.logger.info(f"Router initialized with strategy: {strategy}")

    def add_provider(self, provider: BaseProvider) -> None:
        """Add a provider to the router.

        The provider will be added to the list of available providers
        and can be selected by the router based on the configured strategy.

        Args:
            provider: Provider instance to add. Must be an instance of
                    BaseProvider or its subclass.

        Example:
            ```python
            from orchestrator.providers.base import ProviderConfig
            from orchestrator.providers.mock import MockProvider

            config = ProviderConfig(name="my-provider", model="mock-normal")
            provider = MockProvider(config)
            router.add_provider(provider)
            ```
        """
        self.providers.append(provider)
        self.logger.info(f"Added provider: {provider.config.name}")

    async def route(
        self,
        prompt: str,
        params: GenerationParams | None = None
    ) -> str:
        """Route a request to an appropriate provider based on the strategy.

        This method selects a provider according to the configured routing
        strategy, attempts to generate a response, and automatically falls
        back to other providers if the selected provider fails.

        Args:
            prompt: Input text prompt to generate completion for
            params: Optional generation parameters (temperature, max_tokens, etc.)
                   If None, provider defaults will be used

        Returns:
            Generated text response from the selected provider

        Raises:
            ProviderError: If no providers are registered
            TimeoutError: If all providers timeout
            RateLimitError: If all providers hit rate limit
            AuthenticationError: If all providers fail authentication
            InvalidRequestError: If all providers receive invalid requests
            Exception: Any other exception from the last failed provider

        Example:
            ```python
            # Simple routing
            response = await router.route("What is Python?")

            # With custom parameters
            from orchestrator.providers.base import GenerationParams
            params = GenerationParams(temperature=0.8, max_tokens=500)
            response = await router.route("Write a poem", params=params)
            ```
        """
        # Check if any providers are registered
        if not self.providers:
            raise ProviderError("No providers registered")

        # Select provider based on strategy
        selected_provider = await self._select_provider()

        # Find index of selected provider for fallback logic
        selected_index = self.providers.index(selected_provider)

        # Attempt to generate response with fallback
        last_error: Exception | None = None

        for i in range(len(self.providers)):
            # Calculate provider index (circular, starting from selected)
            index = (selected_index + i) % len(self.providers)
            provider = self.providers[index]

            try:
                self.logger.info(f"Trying provider: {provider.config.name}")
                result = await provider.generate(prompt, params)
                self.logger.info(
                    f"Success with provider: {provider.config.name}"
                )
                return result
            except Exception as e:
                self.logger.warning(
                    f"Provider {provider.config.name} failed: {e}, trying next"
                )
                last_error = e
                continue

        # All providers failed
        self.logger.error("All providers failed")
        if last_error is None:
            raise ProviderError("All providers failed")
        raise last_error

    async def _select_provider(self) -> BaseProvider:
        """Select a provider based on the configured routing strategy.

        This is an internal method that implements the provider selection
        logic for each supported strategy.

        Returns:
            Selected provider instance

        Raises:
            ProviderError: If no providers are available (should not happen
                          as route() checks this first)
        """
        if not self.providers:
            raise ProviderError("No providers available for selection")

        if self.strategy == "round-robin":
            # Round-robin: select in cyclic order
            selected = self.providers[
                self._current_index % len(self.providers)
            ]
            self._current_index += 1
            self.logger.info(
                f"Selected provider: {selected.config.name} "
                f"(strategy: round-robin)"
            )
            return selected

        elif self.strategy == "random":
            # Random: select a random provider
            selected = random.choice(self.providers)
            self.logger.info(
                f"Selected provider: {selected.config.name} "
                f"(strategy: random)"
            )
            return selected

        elif self.strategy == "first-available":
            # First-available: select first healthy provider
            selected = None
            for provider in self.providers:
                if await provider.health_check():
                    selected = provider
                    break

            # If no healthy provider found, fallback to first provider
            if selected is None:
                selected = self.providers[0]
                self.logger.info(
                    f"No healthy providers found, will try all starting with: "
                    f"{selected.config.name} (strategy: first-available)"
                )
            else:
                self.logger.info(
                    f"Selected provider: {selected.config.name} "
                    f"(strategy: first-available)"
                )
            return selected

        else:
            # This should never happen due to validation in __init__
            raise ValueError(f"Unknown strategy: {self.strategy}")

    async def route_stream(
        self,
        prompt: str,
        params: GenerationParams | None = None
    ) -> AsyncIterator[str]:
        """Route request with streaming response.

        This method works like `route()` but yields chunks incrementally as they
        become available. It supports automatic fallback like `route()`, but with
        an important constraint: fallback is only attempted **before** the first
        chunk is yielded. Once streaming has started, any errors will immediately
        raise an exception without trying other providers.

        This behavior ensures that clients receive consistent, coherent responses
        without mixing chunks from different providers mid-stream.

        Args:
            prompt: Input text prompt to generate completion for
            params: Optional generation parameters (temperature, max_tokens, etc.)
                   If None, provider defaults will be used

        Yields:
            Chunks of text from the selected provider as they become available

        Raises:
            ProviderError: If no providers are registered
            TimeoutError: If all providers timeout (before first chunk)
            RateLimitError: If all providers hit rate limit (before first chunk)
            AuthenticationError: If all providers fail authentication (before first chunk)
            InvalidRequestError: If all providers receive invalid requests (before first chunk)
            Exception: Any other exception from the last failed provider (before first chunk)
                       or any exception after the first chunk is yielded

        Example:
            ```python
            # Simple streaming
            async for chunk in router.route_stream("What is Python?"):
                print(chunk, end="", flush=True)

            # With custom parameters
            from orchestrator.providers.base import GenerationParams
            params = GenerationParams(temperature=0.8, max_tokens=500)
            async for chunk in router.route_stream("Write a poem", params=params):
                print(chunk, end="", flush=True)
            ```

        Note:
            Fallback behavior: If an error occurs before the first chunk is yielded,
            the router will automatically try the next provider in the circular order.
            However, once the first chunk is yielded, any subsequent errors will
            immediately raise an exception to prevent mixing chunks from different providers.
        """
        # Check if any providers are registered
        if not self.providers:
            raise ProviderError("No providers registered")

        # Select provider based on strategy
        selected_provider = await self._select_provider()

        # Find index of selected provider for fallback logic
        selected_index = self.providers.index(selected_provider)

        # Attempt to generate response with fallback
        last_error: Exception | None = None

        for i in range(len(self.providers)):
            # Calculate provider index (circular, starting from selected)
            index = (selected_index + i) % len(self.providers)
            provider = self.providers[index]

            try:
                self.logger.info(f"Trying provider: {provider.config.name}")

                # Track if we've yielded the first chunk
                # Once the first chunk is sent, we cannot fallback to another provider
                first_chunk_sent = False

                try:
                    # Stream chunks from the provider
                    async for chunk in provider.generate_stream(prompt, params):
                        # Mark that we've started streaming
                        if not first_chunk_sent:
                            first_chunk_sent = True

                        # Yield the chunk to the caller
                        yield chunk

                    # If we get here, streaming completed successfully
                    self.logger.info(
                        f"Success with provider: {provider.config.name}"
                    )
                    return

                except Exception as stream_error:
                    # If error occurred after first chunk, we cannot fallback
                    # Raise immediately to prevent mixing chunks from different providers
                    if first_chunk_sent:
                        self.logger.error(
                            f"Streaming error after first chunk from provider "
                            f"{provider.config.name}: {stream_error}. "
                            f"Cannot fallback to prevent mixing chunks."
                        )
                        raise

                    # If error occurred before first chunk, we can try next provider
                    raise stream_error

            except Exception as e:
                self.logger.warning(
                    f"Provider {provider.config.name} failed: {e}, trying next"
                )
                last_error = e
                continue

        # All providers failed (before any chunks were yielded)
        self.logger.error("All providers failed")
        if last_error is None:
            raise ProviderError("All providers failed")
        raise last_error
