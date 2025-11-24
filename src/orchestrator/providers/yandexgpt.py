"""YandexGPT provider implementation for Multi-LLM Orchestrator.

This module provides YandexGPTProvider, a full-featured async provider for
YandexGPT (Yandex Cloud) API with IAM authentication, REST API integration, and
comprehensive error handling.

The provider supports:
    - IAM token authentication (user-managed, 12-hour validity)
    - Full parameter support (temperature, maxTokens)
    - Comprehensive error handling and mapping
    - Health check via minimal API request

Example:
    ```python
    from orchestrator.providers import ProviderConfig, YandexGPTProvider
    from orchestrator import Router

    # Create provider
    config = ProviderConfig(
        name="yandexgpt-prod",
        api_key="your_iam_token_here",
        folder_id="your_folder_id_here",
        timeout=60,
        max_retries=3,
        model="yandexgpt/latest"  # or "yandexgpt-lite/latest"
    )
    provider = YandexGPTProvider(config)

    # Use with Router
    router = Router(strategy="round-robin")
    router.add_provider(provider)

    # Generate response
    response = await router.route("What is Python?")
    ```
"""

from typing import Any, cast

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


class YandexGPTProvider(BaseProvider):
    """YandexGPT (Yandex Cloud) LLM provider with IAM authentication.

    This provider implements the BaseProvider interface and provides
    integration with YandexGPT API through IAM token authentication.
    It supports user-managed IAM tokens (12-hour validity), comprehensive
    error handling, and health checks.

    Attributes:
        config: Provider configuration containing IAM token, folder_id,
               timeouts, retry settings, and other options
        logger: Logger instance for this provider
        _client: HTTPX async client for API requests (internal)

    IAM Token Management:
        - IAM token is stored in config.api_key (user-managed)
        - Token validity: 12 hours
        - User is responsible for token refresh
        - On 401 error, AuthenticationError is raised (no auto-refresh)

    Example:
        ```python
        config = ProviderConfig(
            name="yandexgpt",
            api_key="your_iam_token",
            folder_id="your_folder_id",
            model="yandexgpt/latest"
        )
        provider = YandexGPTProvider(config)

        # Simple generation
        response = await provider.generate("Hello, world!")

        # With custom parameters
        params = GenerationParams(temperature=0.8, max_tokens=500)
        response = await provider.generate("Write a poem", params=params)

        # Health check
        is_healthy = await provider.health_check()
        ```
    """

    # API constants
    DEFAULT_BASE_URL: str = "https://llm.api.cloud.yandex.net"
    DEFAULT_MODEL: str = "yandexgpt/latest"
    API_ENDPOINT: str = "/foundationModels/v1/completion"

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize YandexGPT provider with configuration.

        Args:
            config: Provider configuration. Must include:
                - name: Provider identifier
                - api_key: IAM token for authentication (required)
                - folder_id: Yandex Cloud folder ID (required)
                - base_url: Optional API base URL (defaults to YandexGPT API)
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)
                - model: Model name (default: "yandexgpt/latest")

        Raises:
            ValueError: If required configuration (api_key or folder_id) is missing

        Example:
            ```python
            config = ProviderConfig(
                name="yandexgpt",
                api_key="your_iam_token",
                folder_id="your_folder_id",
                model="yandexgpt-lite/latest"
            )
            provider = YandexGPTProvider(config)
            ```
        """
        super().__init__(config)

        # Validate required fields
        if not config.api_key:
            raise ValueError("api_key is required for YandexGPTProvider")
        if not config.folder_id:
            raise ValueError("folder_id is required for YandexGPTProvider")

        # HTTP client with configured timeout and SSL verification
        self._client = httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.verify_ssl
        )

        # Log security warning if SSL verification is disabled
        if not config.verify_ssl:
            self.logger.warning(
                f"SSL certificate verification is DISABLED for provider '{config.name}'. "
                "This is insecure and should only be used in development."
            )

        self.logger.info(
            f"YandexGPTProvider initialized: model={config.model or self.DEFAULT_MODEL}, "
            f"folder_id={config.folder_id}"
        )

    def _build_model_uri(self, model: str | None = None) -> str:
        """Build modelUri from configuration.

        Constructs the model URI in format: gpt://{folder_id}/{model}
        If model already starts with 'gpt://', uses it as-is (for advanced users).

        Args:
            model: Optional model name. If None, uses config.model or DEFAULT_MODEL.

        Returns:
            Model URI string in format: gpt://{folder_id}/{model}

        Example:
            ```python
            # Automatic construction
            uri = provider._build_model_uri()  # gpt://folder123/yandexgpt/latest

            # Custom model
            uri = provider._build_model_uri("yandexgpt-lite/latest")
            # gpt://folder123/yandexgpt-lite/latest

            # Full URI (used as-is)
            uri = provider._build_model_uri("gpt://folder123/yandexgpt/latest")
            # gpt://folder123/yandexgpt/latest (unchanged)
            ```
        """
        # Use provided model, or fallback to config.model, or DEFAULT_MODEL
        model = model or self.config.model or self.DEFAULT_MODEL

        # If model already starts with 'gpt://', use as-is (full URI provided)
        if model.startswith("gpt://"):
            return model

        # Build URI: gpt://{folder_id}/{model}
        return f"gpt://{self.config.folder_id}/{model}"

    async def generate(
        self, prompt: str, params: GenerationParams | None = None
    ) -> str:
        """Generate text completion from a prompt using YandexGPT API.

        This method implements the main text generation functionality:
        1. Builds modelUri from configuration
        2. Prepares API request with model, messages, and generation parameters
        3. Sends POST request to /foundationModels/v1/completion
        4. Parses response and returns generated text

        Args:
            prompt: Input text prompt to generate completion for
            params: Optional generation parameters (temperature, max_tokens)
                   If None, provider defaults will be used (temperature=0.6, max_tokens=1000)
                   Note: top_p and stop are not supported by YandexGPT API

        Returns:
            Generated text response from YandexGPT API

        Raises:
            AuthenticationError: If IAM token is invalid or expired (401, 403)
            RateLimitError: If provider rate limit is exceeded (429)
            TimeoutError: If request times out
            InvalidRequestError: If request parameters are invalid (400, 404)
            ProviderError: For other provider-specific errors

        Example:
            ```python
            # Simple generation
            response = await provider.generate("What is Python?")
            print(response)

            # With custom parameters
            params = GenerationParams(
                temperature=0.8,
                max_tokens=500
            )
            response = await provider.generate("Write a story", params=params)
            ```
        """
        # Build model URI
        model_uri = self._build_model_uri()

        # Prepare API endpoint URL
        base_url = self.config.base_url or self.DEFAULT_BASE_URL
        url = f"{base_url}{self.API_ENDPOINT}"

        # Prepare request headers (all three are required)
        # api_key and folder_id are validated in __init__, so they are not None here
        assert self.config.api_key is not None
        assert self.config.folder_id is not None
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.config.api_key}",
            "x-folder-id": self.config.folder_id,
            "Content-Type": "application/json",
        }

        # Prepare request payload
        # completionOptions must be a nested object
        payload: dict[str, Any] = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": (
                    params.temperature if params and params.temperature is not None else 0.6
                ),
                "maxTokens": params.max_tokens if params and params.max_tokens else 1000,
            },
            "messages": [{"role": "user", "text": prompt}],
        }

        self.logger.debug(
            f"Sending request to YandexGPT API: modelUri={model_uri}, "
            f"prompt_length={len(prompt)}"
        )

        try:
            # Make API request
            response = await self._client.post(url, headers=headers, json=payload)

            # Handle errors
            if response.status_code != 200:
                self._handle_error(response)

            # Parse successful response
            # Response structure: {"result": {"alternatives": [{"message": {"text": "..."}}]}}
            data: dict[str, Any] = cast(dict[str, Any], response.json())
            response_text: str = cast(
                str, data["result"]["alternatives"][0]["message"]["text"]
            )

            self.logger.debug(f"Received response: {len(response_text)} characters")
            return response_text

        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to YandexGPT API timed out after {self.config.timeout}s"
            ) from None
        except httpx.ConnectError as e:
            raise ProviderError(f"Connection error to YandexGPT API: {e}") from e
        except httpx.NetworkError as e:
            raise ProviderError(f"Network error to YandexGPT API: {e}") from e
        except (KeyError, IndexError) as e:
            raise ProviderError(
                f"Invalid response format from YandexGPT API: {e}"
            ) from e
        except (ValueError, TypeError) as e:
            # JSON decode errors (invalid JSON response)
            error_str = str(e)
            if "Expecting value" in error_str or "JSON" in error_str or "decode" in error_str.lower():
                raise ProviderError(
                    "Invalid response format from YandexGPT API: invalid JSON"
                ) from e
            raise ProviderError(f"Unexpected error during generation: {e}") from e
        except ProviderError:
            # Re-raise provider errors (AuthenticationError, RateLimitError, etc.)
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise ProviderError(f"Unexpected error during generation: {e}") from e

    async def health_check(self) -> bool:
        """Check if the provider is healthy and available.

        This method verifies provider health by making a minimal request
        to the YandexGPT API. If the request succeeds (200 status), the
        provider is considered healthy. Uses a short timeout (5 seconds)
        to avoid blocking.

        Returns:
            True if provider is healthy (API accessible and token valid),
            False otherwise

        Example:
            ```python
            is_healthy = await provider.health_check()
            if is_healthy:
                response = await provider.generate("Hello")
            else:
                logger.error("YandexGPT provider is unhealthy")
            ```
        """
        try:
            # Save original timeout
            old_timeout = self._client.timeout
            # Use short timeout for health check (5 seconds)
            self._client.timeout = httpx.Timeout(5.0, connect=5.0)

            # Prepare minimal request
            base_url = self.config.base_url or self.DEFAULT_BASE_URL
            url = f"{base_url}{self.API_ENDPOINT}"

            # api_key and folder_id are validated in __init__, so they are not None here
            assert self.config.api_key is not None
            assert self.config.folder_id is not None
            headers: dict[str, str] = {
                "Authorization": f"Bearer {self.config.api_key}",
                "x-folder-id": self.config.folder_id,
                "Content-Type": "application/json",
            }

            # Minimal payload for health check
            payload = {
                "modelUri": self._build_model_uri(),
                "completionOptions": {"stream": False, "maxTokens": 10},
                "messages": [{"role": "user", "text": "Hi"}],
            }

            # Make minimal request
            response = await self._client.post(url, headers=headers, json=payload)

            # Restore original timeout
            self._client.timeout = old_timeout

            # Health check passed if status is 200
            is_healthy = response.status_code == 200
            if is_healthy:
                self.logger.debug("Health check passed: API accessible and token valid")
            else:
                self.logger.warning(
                    f"Health check failed: API returned status {response.status_code}"
                )
            return is_healthy

        except Exception as e:
            # Restore timeout even on error
            if hasattr(self, "_client"):
                self._client.timeout = old_timeout

            self.logger.warning(f"Health check failed: {e}")
            return False

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API errors and map HTTP status codes to provider exceptions.

        This method parses error responses from YandexGPT API and raises
        appropriate exceptions based on HTTP status codes. Error messages
        are extracted from JSON response if available, otherwise from
        response text.

        Args:
            response: HTTPX response object with error status code

        Raises:
            InvalidRequestError: For 400, 404 status codes
            AuthenticationError: For 401, 403 status codes
            RateLimitError: For 429 status code
            ProviderError: For 500+ status codes and unknown errors

        Example:
            ```python
            # Internal method, called automatically on API errors
            if response.status_code != 200:
                self._handle_error(response)
            ```
        """
        # Extract error message from response
        try:
            error_data = response.json()
            error_message = error_data.get("message", response.text)
        except Exception:
            # Fallback to response text if JSON parsing fails
            error_message = response.text or f"HTTP {response.status_code}"

        # Map status codes to exceptions
        if response.status_code == 400:
            raise InvalidRequestError(f"Bad request: {error_message}")
        elif response.status_code == 401:
            raise AuthenticationError(
                f"Invalid or expired IAM token: {error_message}"
            )
        elif response.status_code == 403:
            raise AuthenticationError(
                f"Access denied (check folder_id and permissions): {error_message}"
            )
        elif response.status_code == 404:
            raise InvalidRequestError(f"Model not found: {error_message}")
        elif response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        elif response.status_code >= 500:
            raise ProviderError(f"Server error: {error_message}")
        else:
            raise ProviderError(
                f"Unknown error (HTTP {response.status_code}): {error_message}"
            )

