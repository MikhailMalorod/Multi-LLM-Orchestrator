"""LLM Router module for managing provider selection and request routing."""

import asyncio
import logging
import random
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .metrics import ProviderMetrics
from .pricing import calculate_cost
from .prometheus_exporter import PrometheusExporter
from .providers.base import BaseProvider, GenerationParams, ProviderError
from .tokenization import count_tokens

# Valid routing strategies
VALID_STRATEGIES = ["round-robin", "random", "first-available", "best-available"]


@dataclass
class UsageData:
    """Usage data for billing and analytics.

    This dataclass contains comprehensive usage information for each
    LLM request, suitable for billing APIs and analytics platforms.

    Attributes:
        provider_name: Provider identifier (e.g., "gigachat", "yandexgpt")
        model: Model name or version (e.g., "GigaChat-Pro")
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens (prompt + completion)
        cost: Cost in RUB for this request
        latency_ms: Request latency in milliseconds
        success: Whether the request succeeded
        streaming: Whether this was a streaming request
        error_type: Exception type name if request failed (e.g., "TimeoutError")
        timestamp: UTC timestamp when request completed

    Example:
        >>> data = UsageData(
        ...     provider_name="gigachat",
        ...     model="GigaChat-Pro",
        ...     prompt_tokens=42,
        ...     completion_tokens=128,
        ...     total_tokens=170,
        ...     cost=3.40,
        ...     latency_ms=1234.56,
        ...     success=True,
        ...     streaming=False,
        ... )
    """

    provider_name: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    latency_ms: float
    success: bool
    streaming: bool
    error_type: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# Type alias for usage callback
UsageCallback = Callable[[UsageData], Awaitable[None]]


class Router:
    """Router for managing LLM provider selection and request routing.

    The Router handles intelligent routing of requests to appropriate
    LLM providers based on configurable routing strategies. It supports
    multiple routing strategies including round-robin, random selection,
    first-available provider selection, and best-available (metrics-based)
    selection with automatic fallback.

    The Router tracks performance metrics for each provider, including
    request counts, latency, error rates, and health status, which can
    be used for intelligent routing decisions.

    Attributes:
        strategy: Routing strategy to use for provider selection
        providers: List of registered provider instances
        metrics: Dictionary mapping provider names to their metrics (internal)
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

    def __init__(
        self,
        strategy: str = "round-robin",
        usage_callback: UsageCallback | None = None,
        callback_url: str | None = None,
        tenant_id: str | None = None,
        platform_key_id: str | None = None,
    ) -> None:
        """Initialize the router with a routing strategy.

        Args:
            strategy: Routing strategy to use. Must be one of:
                - "round-robin": Select providers in a cyclic order
                - "random": Select a random provider from available providers
                - "first-available": Select the first healthy provider
                - "best-available": Select the healthiest provider with lowest latency
            usage_callback: Optional callback function for usage tracking.
                Receives UsageData instance after each request. Useful for
                in-process billing, analytics, or logging. Mutually exclusive
                with callback_url.
            callback_url: Optional HTTP endpoint for usage tracking via POST.
                Useful for remote billing APIs in multi-tenant deployments.
                Mutually exclusive with usage_callback.
            tenant_id: Optional tenant identifier for HTTP callbacks.
                Included in POST payload if provided.
            platform_key_id: Optional platform key identifier for HTTP callbacks.
                Useful for BYOK (Bring Your Own Key) cost attribution.

        Raises:
            ValueError: If the provided strategy is not valid
            ValueError: If both usage_callback and callback_url are specified

        Example:
            ```python
            # Round-robin (default)
            router = Router()

            # Random selection
            router = Router(strategy="random")

            # First available healthy provider
            router = Router(strategy="first-available")

            # With Python callback
            async def track_usage(data: UsageData) -> None:
                print(f"Cost: {data.cost} RUB")
            router = Router(usage_callback=track_usage)

            # With HTTP POST callback
            router = Router(
                callback_url="https://api.example.com/usage",
                tenant_id="tenant-123",
            )
            ```
        """
        # Validate strategy
        if strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy: {strategy}. "
                f"Must be one of {VALID_STRATEGIES}"
            )

        # Validate callback configuration
        if usage_callback and callback_url:
            raise ValueError(
                "Cannot specify both 'usage_callback' and 'callback_url'. "
                "Use 'usage_callback' for in-process Python callbacks, "
                "or 'callback_url' for remote HTTP POST callbacks."
            )

        self.strategy = strategy
        self.providers: list[BaseProvider] = []
        self.metrics: dict[str, ProviderMetrics] = {}
        self._current_index: int = 0
        self.logger = logging.getLogger("orchestrator.router")

        # Usage tracking configuration
        self.usage_callback = usage_callback
        self.callback_url = callback_url
        self.tenant_id = tenant_id
        self.platform_key_id = platform_key_id

        # Prometheus exporter (v0.7.0+, not started by default)
        self._prometheus_exporter: PrometheusExporter | None = None
        self._metrics_update_task: asyncio.Task[None] | None = None

        self.logger.info(f"Router initialized with strategy: {strategy}")

    def add_provider(self, provider: BaseProvider) -> None:
        """Add a provider to the router.

        The provider will be added to the list of available providers
        and can be selected by the router based on the configured strategy.
        Metrics tracking is automatically initialized for the provider.

        Args:
            provider: Provider instance to add. Must be an instance of
                    BaseProvider or its subclass.

        Raises:
            ValueError: If a provider with the same name already exists

        Example:
            ```python
            from orchestrator.providers.base import ProviderConfig
            from orchestrator.providers.mock import MockProvider

            config = ProviderConfig(name="my-provider", model="mock-normal")
            provider = MockProvider(config)
            router.add_provider(provider)
            ```
        """
        # Check for duplicate provider names
        provider_name = provider.config.name
        if provider_name in self.metrics:
            raise ValueError(
                f"Provider with name '{provider_name}' already exists"
            )
        # Check if name exists in providers list
        for existing_provider in self.providers:
            if existing_provider.config.name == provider_name:
                raise ValueError(
                    f"Provider with name '{provider_name}' already exists"
                )

        self.providers.append(provider)
        # Initialize metrics for the new provider
        self.metrics[provider_name] = ProviderMetrics()
        self.logger.info(f"Added provider: {provider_name}")

    async def update_providers(
        self,
        new_providers: list[BaseProvider],
        preserve_metrics: bool = False,
    ) -> None:
        """Update providers without recreating Router.

        Zero-downtime provider swap. Active requests continue on old providers,
        new requests use updated provider list.

        Args:
            new_providers: List of new provider instances
            preserve_metrics: If True, preserve metrics for providers with matching names.
                             If False (default), reset all metrics.

        Raises:
            ValueError: If new_providers is empty or contains duplicate names

        Example:
            ```python
            # Simple update (reset metrics)
            new_gigachat = GigaChatProvider(config1)
            new_yandex = YandexGPTProvider(config2)
            await router.update_providers([new_gigachat, new_yandex])

            # Preserve metrics for matching provider names
            await router.update_providers([new_gigachat], preserve_metrics=True)
            ```
        """
        # 1. Validation (before any changes)
        if not new_providers:
            raise ValueError("new_providers cannot be empty")

        # Check for duplicates in new_providers
        new_names = [p.config.name for p in new_providers]
        if len(new_names) != len(set(new_names)):
            duplicates = [name for name in new_names if new_names.count(name) > 1]
            raise ValueError(
                f"Duplicate provider names in new_providers: {set(duplicates)}"
            )

        # 2. Detect model changes (BEFORE clearing self.providers)
        if preserve_metrics:
            # Build lookup dict for O(1) access
            old_providers_by_name = {p.config.name: p for p in self.providers}

            for provider in new_providers:
                name = provider.config.name
                old_provider = old_providers_by_name.get(name)
                if old_provider and old_provider.config.model != provider.config.model:
                    self.logger.warning(
                        f"Provider '{name}' model changed: "
                        f"{old_provider.config.model} → {provider.config.model}. "
                        f"Metrics preserved but may be inconsistent."
                    )

        # 3. Handle metrics
        if preserve_metrics:
            new_provider_names = {p.config.name for p in new_providers}

            # Remove metrics for providers not in new list
            metrics_to_remove = [
                name for name in list(self.metrics.keys())
                if name not in new_provider_names
            ]
            for name in metrics_to_remove:
                del self.metrics[name]

            # Create metrics for new providers (if not exist)
            for provider in new_providers:
                if provider.config.name not in self.metrics:
                    self.metrics[provider.config.name] = ProviderMetrics()
        else:
            # Reset all metrics and create for new providers
            self.metrics.clear()
            for provider in new_providers:
                self.metrics[provider.config.name] = ProviderMetrics()

        # 4. Atomic provider swap
        self.providers.clear()
        self.providers.extend(new_providers)

        # 5. Reset round-robin index
        self._current_index = 0

        # 6. Logging
        self.logger.info(
            "providers_updated",
            extra={
                "provider_count": len(new_providers),
                "provider_names": [p.config.name for p in new_providers],
                "metrics_preserved": preserve_metrics,
            },
        )

    def _log_request_event(
        self,
        provider_name: str,
        model: str | None,
        latency_ms: float,
        streaming: bool,
        success: bool,
        error_type: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        cost: float | None = None,
    ) -> None:
        """Log a request event with structured fields.

        This helper method provides consistent logging format for request
        completion and failure events across route() and route_stream().

        Args:
            provider_name: Name of the provider that handled the request
            model: Model name used (if available)
            latency_ms: Request latency in milliseconds
            streaming: Whether this was a streaming request
            success: Whether the request was successful
            error_type: Type of error (if request failed)
            prompt_tokens: Number of prompt tokens (optional, v0.7.0+)
            completion_tokens: Number of completion tokens (optional, v0.7.0+)
            total_tokens: Total tokens (optional, v0.7.0+)
            cost: Request cost in RUB (optional, v0.7.0+)
        """
        extra = {
            "provider": provider_name,
            "model": model,
            "latency_ms": latency_ms,
            "streaming": streaming,
            "success": success,
        }
        if error_type:
            extra["error_type"] = error_type

        # Add token and cost info (v0.7.0+) if available
        if prompt_tokens is not None:
            extra["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            extra["completion_tokens"] = completion_tokens
        if total_tokens is not None:
            extra["total_tokens"] = total_tokens
        if cost is not None:
            extra["cost_rub"] = round(cost, 2)  # Round to 2 decimals for logs

        if success:
            self.logger.info("llm_request_completed", extra=extra)
        else:
            self.logger.warning("llm_request_failed", extra=extra)

    async def _invoke_usage_callback(
        self,
        provider_name: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_ms: float,
        success: bool,
        streaming: bool,
        error_type: str | None = None,
    ) -> None:
        """Invoke usage callback (Python function or HTTP POST).

        This method invokes the configured usage callback with request
        usage data. Supports two callback types:

        1. Python callback (usage_callback): Calls an async Python function
           with UsageData instance. Useful for in-process analytics.

        2. HTTP POST callback (callback_url): POSTs usage data as JSON to
           a remote endpoint. Useful for remote billing APIs.

        Errors in callbacks are logged but do not disrupt the main request
        flow (fail-silent behavior).

        Args:
            provider_name: Provider identifier (e.g., "gigachat")
            model: Model name or version
            prompt_tokens: Number of tokens in prompt
            completion_tokens: Number of tokens in completion
            cost: Cost in RUB
            latency_ms: Request latency in milliseconds
            success: Whether the request succeeded
            streaming: Whether this was a streaming request
            error_type: Exception type name if request failed

        Example:
            >>> await self._invoke_usage_callback(
            ...     provider_name="gigachat",
            ...     model="GigaChat-Pro",
            ...     prompt_tokens=42,
            ...     completion_tokens=128,
            ...     cost=3.40,
            ...     latency_ms=1234.56,
            ...     success=True,
            ...     streaming=False,
            ... )
        """
        total_tokens = prompt_tokens + completion_tokens

        # Option 1: Python callback
        if self.usage_callback:
            try:
                usage_data = UsageData(
                    provider_name=provider_name,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    success=success,
                    streaming=streaming,
                    error_type=error_type,
                )
                await self.usage_callback(usage_data)
            except Exception as e:
                # Fail silently - callback errors should not disrupt requests
                self.logger.warning(f"Usage callback failed: {e}")

        # Option 2: HTTP POST callback
        elif self.callback_url:
            try:
                import httpx

                # Build payload (snake_case for consistency with Python)
                payload = {
                    "provider": provider_name,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost,
                    "latency_ms": latency_ms,
                    "success": success,
                    "streaming": streaming,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                # Add optional context fields
                if self.tenant_id:
                    payload["tenant_id"] = self.tenant_id
                if self.platform_key_id:
                    payload["platform_key_id"] = self.platform_key_id
                if error_type:
                    payload["error_type"] = error_type

                # POST to callback URL (5 second timeout)
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(self.callback_url, json=payload)
            except Exception as e:
                # Fail silently - callback errors should not disrupt requests
                self.logger.warning(f"HTTP callback failed: {e}")

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

            # Measure time for metrics
            start_time = time.perf_counter()

            try:
                self.logger.info(f"Trying provider: {provider.config.name}")
                result = await provider.generate(prompt, params)

                # Calculate latency
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Count tokens (v0.7.0+)
                prompt_tokens = count_tokens(prompt)
                completion_tokens = count_tokens(result)
                total_tokens = prompt_tokens + completion_tokens

                # Calculate cost (v0.7.0+)
                cost = calculate_cost(
                    provider_name=provider.config.name,
                    model=provider.config.model,
                    total_tokens=total_tokens,
                )

                # Update metrics with tokens and cost
                # Use get() to handle race condition with update_providers()
                metrics = self.metrics.get(provider.config.name)
                if metrics is None:
                    # Metrics were removed during update_providers(), create new one
                    metrics = ProviderMetrics()
                    self.metrics[provider.config.name] = metrics
                metrics.record_success(
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost=cost,
                )

                # Log success event with token info
                self._log_request_event(
                    provider_name=provider.config.name,
                    model=provider.config.model,
                    latency_ms=latency_ms,
                    streaming=False,
                    success=True,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    cost=cost,
                )

                # Invoke usage callback (success)
                await self._invoke_usage_callback(
                    provider_name=provider.config.name,
                    model=provider.config.model or "",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    success=True,
                    streaming=False,
                )

                self.logger.info(
                    f"Success with provider: {provider.config.name}"
                )
                return result
            except Exception as e:
                # Calculate latency even for failed requests
                latency_ms = (time.perf_counter() - start_time) * 1000
                # Use get() to handle race condition with update_providers()
                metrics = self.metrics.get(provider.config.name)
                if metrics is None:
                    # Metrics were removed during update_providers(), create new one
                    metrics = ProviderMetrics()
                    self.metrics[provider.config.name] = metrics
                metrics.record_error(
                    latency_ms, datetime.now(UTC)
                )

                # Log failure event
                self._log_request_event(
                    provider_name=provider.config.name,
                    model=provider.config.model,
                    latency_ms=latency_ms,
                    streaming=False,
                    success=False,
                    error_type=type(e).__name__,
                )

                # Invoke usage callback (error)
                await self._invoke_usage_callback(
                    provider_name=provider.config.name,
                    model=provider.config.model or "",
                    prompt_tokens=0,
                    completion_tokens=0,
                    cost=0.0,
                    latency_ms=latency_ms,
                    success=False,
                    streaming=False,
                    error_type=type(e).__name__,
                )

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

        elif self.strategy == "best-available":
            # Best-available: select healthiest provider with lowest latency
            return self._select_best_available_provider()

        else:
            # This should never happen due to validation in __init__
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _effective_latency_for_sort(self, metrics: ProviderMetrics) -> float:
        """Calculate effective latency for sorting providers.

        Uses rolling_avg_latency_ms if available, falls back to avg_latency_ms,
        or returns infinity if no latency data is available.

        Args:
            metrics: ProviderMetrics instance to calculate effective latency for

        Returns:
            Effective latency in milliseconds, or float("inf") if no data
        """
        if metrics.rolling_avg_latency_ms is not None:
            return metrics.rolling_avg_latency_ms
        if metrics.avg_latency_ms > 0:
            return metrics.avg_latency_ms
        return float("inf")

    def _select_best_available_provider(self) -> BaseProvider:
        """Select the best available provider based on health and latency.

        Groups providers by health status (healthy > degraded > unhealthy),
        then selects the provider with lowest effective latency within the
        best available group.

        Returns:
            Selected provider instance

        Raises:
            ProviderError: If no providers are available
        """
        if not self.providers:
            raise ProviderError("No providers available for selection")

        # Group providers by health status
        healthy_providers: list[BaseProvider] = []
        degraded_providers: list[BaseProvider] = []
        unhealthy_providers: list[BaseProvider] = []

        for provider in self.providers:
            # Get or create metrics for provider
            metrics = self.metrics.get(provider.config.name)
            if metrics is None:
                # Edge case: provider added but metrics not initialized
                metrics = ProviderMetrics()
                self.metrics[provider.config.name] = metrics

            status = metrics.health_status

            if status == "healthy":
                healthy_providers.append(provider)
            elif status == "degraded":
                degraded_providers.append(provider)
            else:  # unhealthy
                unhealthy_providers.append(provider)

        # Select group by priority: healthy > degraded > unhealthy
        selected_group: list[BaseProvider]
        if healthy_providers:
            selected_group = healthy_providers
        elif degraded_providers:
            selected_group = degraded_providers
        else:
            # Even if all unhealthy, we still select among them
            selected_group = unhealthy_providers

        # Sort by effective latency (ascending)
        selected_group.sort(
            key=lambda p: self._effective_latency_for_sort(
                self.metrics[p.config.name]
            )
        )

        selected = selected_group[0]
        metrics = self.metrics[selected.config.name]
        effective_latency = self._effective_latency_for_sort(metrics)

        self.logger.info(
            f"Selected provider: {selected.config.name} "
            f"(strategy: best-available, health: {metrics.health_status}, "
            f"latency: {effective_latency:.1f}ms)"
        )

        return selected

    def get_metrics(self) -> dict[str, ProviderMetrics]:
        """Return a shallow copy of provider metrics.

        Returns a snapshot of all provider metrics keyed by provider name.
        The returned dictionary is a shallow copy, so modifications to
        the dictionary itself won't affect the router's internal metrics,
        but modifications to ProviderMetrics objects will.

        Returns:
            Dictionary mapping provider names to their metrics.
            Returns empty dict if no providers are registered.

        Example:
            ```python
            metrics = router.get_metrics()
            for provider_name, provider_metrics in metrics.items():
                print(f"{provider_name}: {provider_metrics.health_status}")
                print(f"  Success rate: {provider_metrics.success_rate:.2%}")
                print(f"  Avg latency: {provider_metrics.avg_latency_ms:.1f}ms")
            ```
        """
        return dict(self.metrics)

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

            # Measure time for metrics
            start_time = time.perf_counter()

            try:
                self.logger.info(f"Trying provider: {provider.config.name}")

                # Track if we've yielded the first chunk
                # Once the first chunk is sent, we cannot fallback to another provider
                first_chunk_sent = False

                # Accumulate chunks for token counting (v0.7.0+)
                accumulated_chunks: list[str] = []

                try:
                    # Stream chunks from the provider
                    async for chunk in provider.generate_stream(prompt, params):
                        # Mark that we've started streaming
                        if not first_chunk_sent:
                            first_chunk_sent = True

                        # Accumulate chunks for token counting
                        accumulated_chunks.append(chunk)

                        # Yield the chunk to the caller
                        yield chunk

                    # If we get here, streaming completed successfully
                    # Calculate latency
                    latency_ms = (time.perf_counter() - start_time) * 1000

                    # Reconstruct full response for tokenization (v0.7.0+)
                    full_response = "".join(accumulated_chunks)

                    # Count tokens (v0.7.0+)
                    prompt_tokens = count_tokens(prompt)
                    completion_tokens = count_tokens(full_response)
                    total_tokens = prompt_tokens + completion_tokens

                    # Calculate cost (v0.7.0+)
                    cost = calculate_cost(
                        provider_name=provider.config.name,
                        model=provider.config.model,
                        total_tokens=total_tokens,
                    )

                    # Update metrics with tokens and cost
                    # Use get() to handle race condition with update_providers()
                    metrics = self.metrics.get(provider.config.name)
                    if metrics is None:
                        # Metrics were removed during update_providers(), create new one
                        metrics = ProviderMetrics()
                        self.metrics[provider.config.name] = metrics
                    metrics.record_success(
                        latency_ms=latency_ms,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        cost=cost,
                    )

                    # Log success event with token info
                    self._log_request_event(
                        provider_name=provider.config.name,
                        model=provider.config.model,
                        latency_ms=latency_ms,
                        streaming=True,
                        success=True,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        cost=cost,
                    )

                    # Invoke usage callback (success, streaming)
                    await self._invoke_usage_callback(
                        provider_name=provider.config.name,
                        model=provider.config.model or "",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        cost=cost,
                        latency_ms=latency_ms,
                        success=True,
                        streaming=True,
                    )

                    self.logger.info(
                        f"Success with provider: {provider.config.name}"
                    )
                    return

                except Exception as stream_error:
                    # Calculate latency even for failed requests
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    # Use get() to handle race condition with update_providers()
                    metrics = self.metrics.get(provider.config.name)
                    if metrics is None:
                        # Metrics were removed during update_providers(), create new one
                        metrics = ProviderMetrics()
                        self.metrics[provider.config.name] = metrics
                    metrics.record_error(
                        latency_ms, datetime.now(UTC)
                    )

                    # Log failure event
                    self._log_request_event(
                        provider_name=provider.config.name,
                        model=provider.config.model,
                        latency_ms=latency_ms,
                        streaming=True,
                        success=False,
                        error_type=type(stream_error).__name__,
                    )

                    # Invoke usage callback (error, streaming)
                    await self._invoke_usage_callback(
                        provider_name=provider.config.name,
                        model=provider.config.model or "",
                        prompt_tokens=0,
                        completion_tokens=0,
                        cost=0.0,
                        latency_ms=latency_ms,
                        success=False,
                        streaming=True,
                        error_type=type(stream_error).__name__,
                    )

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

    async def start_metrics_server(self, port: int = 9090) -> None:
        """Start Prometheus metrics HTTP server.

        This method starts an HTTP server that exposes Prometheus metrics
        at /metrics endpoint. The server runs in the background and updates
        metrics every 1 second.

        Args:
            port: HTTP server port (default: 9090).
                 Choose different port if 9090 is already in use.

        Raises:
            OSError: If port is already in use
            RuntimeError: If metrics server is already running

        Example:
            ```python
            router = Router(strategy="best-available")
            router.add_provider(provider)

            # Start metrics server
            await router.start_metrics_server(port=9090)

            # Make requests
            response = await router.route("Hello!")

            # Metrics available at http://localhost:9090/metrics
            ```

        Note:
            The metrics server must be explicitly stopped using stop_metrics_server()
            to ensure graceful shutdown.
        """
        if self._prometheus_exporter is not None:
            raise RuntimeError(
                "Metrics server is already running. "
                "Call stop_metrics_server() first."
            )

        self._prometheus_exporter = PrometheusExporter(port=port)
        await self._prometheus_exporter.start()

        # Start background task to update metrics periodically
        self._metrics_update_task = asyncio.create_task(
            self._update_metrics_loop()
        )

        self.logger.info(
            f"Metrics server started at http://0.0.0.0:{port}/metrics"
        )

    async def stop_metrics_server(self) -> None:
        """Stop Prometheus metrics HTTP server gracefully.

        This method stops the metrics server and cancels the background
        metrics update task. Safe to call even if server is not running.

        Example:
            ```python
            # Start server
            await router.start_metrics_server()

            # ... make requests ...

            # Stop server
            await router.stop_metrics_server()
            ```

        Note:
            This method should be called during application shutdown to
            ensure proper cleanup of resources.
        """
        # Cancel background update task
        if self._metrics_update_task:
            self._metrics_update_task.cancel()
            try:
                await self._metrics_update_task
            except asyncio.CancelledError:
                pass
            self._metrics_update_task = None

        # Stop HTTP server
        if self._prometheus_exporter:
            await self._prometheus_exporter.stop()
            self._prometheus_exporter = None

        self.logger.info("Metrics server stopped")

    async def _update_metrics_loop(self) -> None:
        """Background task to update Prometheus metrics every 1 second.

        This is an internal method that runs in the background and periodically
        updates Prometheus metrics from ProviderMetrics data.

        Note:
            This method runs indefinitely until cancelled. It should not be
            called directly - use start_metrics_server() instead.
        """
        while True:
            try:
                if self._prometheus_exporter:
                    self._prometheus_exporter.update_metrics(self.metrics)
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(1.0)
