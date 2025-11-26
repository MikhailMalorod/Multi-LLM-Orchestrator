"""GigaChat provider implementation for Multi-LLM Orchestrator.

This module provides GigaChatProvider, a full-featured async provider for
GigaChat (Sber) API with OAuth2 authentication, REST API integration, and
comprehensive error handling.

The provider supports:
    - OAuth2 authentication with automatic token refresh
    - Thread-safe token management
    - Full parameter support (temperature, max_tokens, top_p, stop)
    - Comprehensive error handling and mapping
    - Health check via OAuth2 validation

Example:
    ```python
    from orchestrator.providers import ProviderConfig, GigaChatProvider
    from orchestrator import Router

    # Create provider
    config = ProviderConfig(
        name="gigachat-prod",
        api_key="your_authorization_key_here",
        base_url="https://gigachat.devices.sberbank.ru/api/v1",
        timeout=60,
        max_retries=3,
        model="GigaChat",
        scope="GIGACHAT_API_PERS"
    )
    provider = GigaChatProvider(config)

    # Use with Router
    router = Router(strategy="round-robin")
    router.add_provider(provider)

    # Generate response
    response = await router.route("What is Python?")
    ```
"""

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
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


class GigaChatProvider(BaseProvider):
    """GigaChat (Sber) LLM provider with OAuth2 authentication.

    This provider implements the BaseProvider interface and provides
    integration with GigaChat API through OAuth2 authentication flow.
    It supports automatic token refresh, thread-safe token management,
    and comprehensive error handling.

    Attributes:
        config: Provider configuration containing API credentials,
               timeouts, retry settings, and other options
        logger: Logger instance for this provider
        _access_token: Current OAuth2 access token (internal)
        _token_expires_at: Token expiration timestamp in seconds (internal)
        _token_lock: Async lock for thread-safe token updates (internal)
        _client: HTTPX async client for API requests (internal)

    OAuth2 Flow:
        1. Authorization key is used to obtain access_token via OAuth2 endpoint
        2. Access token is valid for ~30 minutes (expires_at in response)
        3. Token is automatically refreshed before expiration (60s buffer)
        4. If token expires during request (401), it's refreshed and request retried

    Example:
        ```python
        config = ProviderConfig(
            name="gigachat",
            api_key="your_authorization_key",
            model="GigaChat",
            scope="GIGACHAT_API_PERS"
        )
        provider = GigaChatProvider(config)

        # Simple generation
        response = await provider.generate("Hello, world!")

        # With custom parameters
        params = GenerationParams(temperature=0.8, max_tokens=500)
        response = await provider.generate("Write a poem", params=params)

        # Health check
        is_healthy = await provider.health_check()
        ```
    """

    # OAuth2 and API constants
    OAUTH_URL: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    DEFAULT_BASE_URL: str = "https://gigachat.devices.sberbank.ru/api/v1"
    DEFAULT_SCOPE: str = "GIGACHAT_API_PERS"
    DEFAULT_MODEL: str = "GigaChat"

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize GigaChat provider with configuration.

        Args:
            config: Provider configuration. Must include:
                - name: Provider identifier
                - api_key: Authorization key for OAuth2 (required)
                - base_url: Optional API base URL (defaults to GigaChat API)
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)
                - model: Model name (default: "GigaChat")
                - scope: OAuth2 scope (default: "GIGACHAT_API_PERS")

        Raises:
            ValueError: If required configuration is missing

        Example:
            ```python
            config = ProviderConfig(
                name="gigachat",
                api_key="your_key_here",
                model="GigaChat-Pro",
                scope="GIGACHAT_API_CORP"
            )
            provider = GigaChatProvider(config)
            ```
        """
        super().__init__(config)

        # Validate required fields
        if not config.api_key:
            raise ValueError("api_key is required for GigaChatProvider")

        # Token management state
        self._access_token: str | None = None
        self._token_expires_at: float | None = None  # timestamp in seconds
        self._token_lock = asyncio.Lock()

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
            f"GigaChatProvider initialized: model={config.model or self.DEFAULT_MODEL}, "
            f"scope={config.scope or self.DEFAULT_SCOPE}"
        )

    async def _ensure_access_token(self) -> str:
        """Ensure valid access token, refresh if needed.

        This method implements thread-safe OAuth2 token management:
        1. Checks if current token is valid (with 60s buffer before expiration)
        2. If token is missing or expired, requests a new one via OAuth2 endpoint
        3. Uses async lock to prevent concurrent token refresh requests

        The token expiration time is stored in seconds (converted from milliseconds
        in the API response) for easier comparison with time.time().

        Returns:
            Valid access token string

        Raises:
            AuthenticationError: If authorization key is invalid (401 response)
            ProviderError: If OAuth2 request fails for other reasons

        Example:
            ```python
            # Token is automatically managed, no need to call directly
            # But can be used for explicit token refresh:
            token = await provider._ensure_access_token()
            ```
        """
        async with self._token_lock:
            # Check if token exists and is still valid (with 60s buffer)
            current_time = time.time()
            if (
                self._access_token is not None
                and self._token_expires_at is not None
                and current_time < self._token_expires_at - 60
            ):
                # Token is valid, return it
                return self._access_token

            # Token is missing or expired, request new one
            self.logger.debug("Fetching new OAuth2 token...")

            # Prepare OAuth2 request
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"scope": self.config.scope or self.DEFAULT_SCOPE}

            try:
                # Request access token
                response = await self._client.post(
                    self.OAUTH_URL, headers=headers, data=data
                )

                # Handle authentication errors
                if response.status_code == 401:
                    raise AuthenticationError("Invalid authorization key")

                # Raise for other HTTP errors
                response.raise_for_status()

                # Parse token response
                token_data = response.json()
                self._access_token = token_data["access_token"]

                # Convert expires_at from milliseconds to seconds
                # expires_at is timestamp in milliseconds from API
                expires_at_ms = token_data["expires_at"]
                self._token_expires_at = expires_at_ms / 1000.0

                self.logger.info(
                    f"OAuth2 token refreshed, expires at {self._token_expires_at:.0f} "
                    f"(in {self._token_expires_at - current_time:.0f}s)"
                )

                return self._access_token

            except httpx.TimeoutException:
                raise TimeoutError("OAuth2 token request timed out") from None
            except httpx.ConnectError as e:
                raise ProviderError(f"OAuth2 connection error: {e}") from e
            except httpx.NetworkError as e:
                raise ProviderError(f"OAuth2 network error: {e}") from e
            except AuthenticationError:
                # Re-raise authentication errors
                raise
            except Exception as e:
                # Catch any other errors
                raise ProviderError(f"OAuth2 token request failed: {e}") from e

    async def generate(
        self, prompt: str, params: GenerationParams | None = None
    ) -> str:
        """Generate text completion from a prompt using GigaChat API.

        This method implements the main text generation functionality:
        1. Ensures valid OAuth2 access token
        2. Prepares API request with model, messages, and generation parameters
        3. Sends POST request to /api/v1/chat/completions
        4. Handles token expiration (401) with automatic refresh and retry
        5. Parses response and returns generated text

        The method automatically handles token refresh if a 401 error occurs
        during the request, retrying the request once with a fresh token.

        Args:
            prompt: Input text prompt to generate completion for
            params: Optional generation parameters (temperature, max_tokens, etc.)
                   If None, provider defaults will be used

        Returns:
            Generated text response from GigaChat API

        Raises:
            AuthenticationError: If API authentication fails (after retry)
            RateLimitError: If provider rate limit is exceeded
            TimeoutError: If request times out
            InvalidRequestError: If request parameters are invalid
            ProviderError: For other provider-specific errors

        Example:
            ```python
            # Simple generation
            response = await provider.generate("What is Python?")
            print(response)

            # With custom parameters
            params = GenerationParams(
                temperature=0.8,
                max_tokens=500,
                top_p=0.9,
                stop=["###", "END"]
            )
            response = await provider.generate("Write a story", params=params)
            ```
        """
        # Ensure valid access token before making request
        await self._ensure_access_token()

        # Prepare API endpoint URL
        base_url = self.config.base_url or self.DEFAULT_BASE_URL
        url = f"{base_url}/chat/completions"

        # Prepare request headers
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        # Prepare request payload
        payload: dict[str, Any] = {
            "model": self.config.model or self.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add optional generation parameters from params
        if params:
            if params.max_tokens:
                payload["max_tokens"] = params.max_tokens
            if params.temperature is not None:
                payload["temperature"] = params.temperature
            if params.top_p is not None:
                payload["top_p"] = params.top_p
            if params.stop:
                payload["stop"] = params.stop

        self.logger.debug(
            f"Sending request to GigaChat API: model={payload['model']}, "
            f"prompt_length={len(prompt)}"
        )

        try:
            # Make API request
            response = await self._client.post(url, headers=headers, json=payload)

            # Handle token expiration: refresh and retry once
            if response.status_code == 401:
                self.logger.warning(
                    "Token expired during request, refreshing and retrying..."
                )
                # Force token refresh by clearing current token
                # (401 means token is invalid regardless of expiration time)
                async with self._token_lock:
                    self._access_token = None
                    self._token_expires_at = None
                # Refresh token
                await self._ensure_access_token()
                # Update headers with new token and new RqUID
                headers["Authorization"] = f"Bearer {self._access_token}"
                headers["RqUID"] = str(uuid.uuid4())
                # Retry request
                response = await self._client.post(url, headers=headers, json=payload)

            # Handle other errors
            if response.status_code != 200:
                self._handle_error(response)

            # Parse successful response
            data: dict[str, Any] = cast(dict[str, Any], response.json())
            response_text: str = cast(str, data["choices"][0]["message"]["content"])

            self.logger.debug(f"Received response: {len(response_text)} characters")
            return response_text

        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to GigaChat API timed out after {self.config.timeout}s"
            ) from None
        except httpx.ConnectError as e:
            raise ProviderError(f"Connection error to GigaChat API: {e}") from e
        except httpx.NetworkError as e:
            raise ProviderError(f"Network error to GigaChat API: {e}") from e
        except (KeyError, IndexError) as e:
            raise ProviderError(f"Invalid response format from GigaChat API: {e}") from e
        except ProviderError:
            # Re-raise provider errors (AuthenticationError, RateLimitError, etc.)
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise ProviderError(f"Unexpected error during generation: {e}") from e

    async def health_check(self) -> bool:
        """Check if the provider is healthy and available.

        This method verifies provider health by attempting to obtain a valid
        OAuth2 access token. If token can be obtained, provider is considered
        healthy. Uses a short timeout (5 seconds) to avoid blocking.

        Returns:
            True if provider is healthy (OAuth2 token can be obtained),
            False otherwise

        Example:
            ```python
            is_healthy = await provider.health_check()
            if is_healthy:
                response = await provider.generate("Hello")
            else:
                logger.error("GigaChat provider is unhealthy")
            ```
        """
        try:
            # Save original timeout
            old_timeout = self._client.timeout
            # Use short timeout for health check (5 seconds)
            self._client.timeout = httpx.Timeout(5.0, connect=5.0)

            # Try to get access token (validates OAuth2 and API availability)
            await self._ensure_access_token()

            # Restore original timeout
            self._client.timeout = old_timeout

            self.logger.debug("Health check passed: OAuth2 token obtained")
            return True

        except Exception as e:
            # Restore timeout even on error
            if hasattr(self, "_client"):
                self._client.timeout = old_timeout

            self.logger.warning(f"Health check failed: {e}")
            return False

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API errors and map HTTP status codes to provider exceptions.

        This method parses error responses from GigaChat API and raises
        appropriate exceptions based on HTTP status codes. Error messages
        are extracted from JSON response if available, otherwise from
        response text.

        Args:
            response: HTTPX response object with error status code

        Raises:
            InvalidRequestError: For 400, 404, 422 status codes
            AuthenticationError: For 401 status code
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
            raise AuthenticationError(f"Authentication failed: {error_message}")
        elif response.status_code == 404:
            raise InvalidRequestError(f"Invalid model or endpoint: {error_message}")
        elif response.status_code == 422:
            raise InvalidRequestError(f"Validation error: {error_message}")
        elif response.status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        elif response.status_code >= 500:
            raise ProviderError(f"Server error: {error_message}")
        else:
            raise ProviderError(f"Unknown error (HTTP {response.status_code}): {error_message}")

    async def _parse_sse_stream(
        self, response: httpx.Response
    ) -> AsyncIterator[str]:
        """Parse Server-Sent Events (SSE) stream from GigaChat API.

        This helper method parses SSE format responses from GigaChat streaming
        endpoint. It extracts text content from each SSE event and yields chunks
        incrementally.

        SSE Format:
            - Each line starts with "data: " prefix
            - Content is JSON: {"choices":[{"delta":{"content":"..."}}]}
            - Stream ends with "data: [DONE]"

        Args:
            response: HTTPX streaming response object

        Yields:
            Text content chunks from the SSE stream. Each chunk is extracted from
            choices[0].delta.content in the JSON payload.

        Note:
            This method handles parsing errors gracefully: if a line cannot be
            parsed as JSON or doesn't contain expected structure, it logs a warning
            and continues to the next line. This ensures streaming continues even
            if some events are malformed.
        """
        async for line in response.aiter_lines():
            # Skip empty lines and lines that don't start with "data: "
            if not line or not line.startswith("data: "):
                continue

            # Extract data after "data: " prefix
            data_str = line[6:].strip()  # Remove "data: " prefix and whitespace

            # Check for end-of-stream marker
            if data_str == "[DONE]":
                break

            # Parse JSON payload
            try:
                data = json.loads(data_str)
                # Extract content from choices[0].delta.content
                # Structure: {"choices":[{"delta":{"content":"..."}}]}
                content = (
                    data.get("choices", [{}])[0]
                    .get("delta", {})
                    .get("content", "")
                )

                # Only yield non-empty content
                if content:
                    yield content

            except json.JSONDecodeError as e:
                # Log warning but continue processing (some events might be malformed)
                self.logger.warning(
                    f"Failed to parse SSE JSON chunk: {data_str[:100]}. Error: {e}"
                )
                continue
            except (KeyError, IndexError, TypeError) as e:
                # Log warning for missing expected structure
                self.logger.warning(
                    f"Unexpected SSE structure in chunk: {data_str[:100]}. Error: {e}"
                )
                continue

    async def generate_stream(
        self, prompt: str, params: GenerationParams | None = None
    ) -> AsyncIterator[str]:
        """Generate text completion with streaming via Server-Sent Events (SSE).

        This method implements streaming text generation using GigaChat's SSE
        endpoint. It works similarly to `generate()`, but yields chunks incrementally
        as they arrive from the API instead of waiting for the complete response.

        The method handles:
        1. OAuth2 token management (automatic refresh)
        2. 401 authentication errors (retry once before streaming starts)
        3. SSE stream parsing and content extraction
        4. Error handling consistent with `generate()`

        Important: Token refresh (401 handling) only works **before** the first chunk
        is yielded. Once streaming starts, any errors will raise exceptions immediately.

        Args:
            prompt: Input text prompt to generate completion for
            params: Optional generation parameters (temperature, max_tokens, etc.)
                   If None, provider defaults will be used

        Yields:
            Chunks of generated text as they arrive from GigaChat API. Each chunk
            is extracted from the SSE stream's choices[0].delta.content field.

        Raises:
            AuthenticationError: If API authentication fails (after retry)
            RateLimitError: If provider rate limit is exceeded
            TimeoutError: If request times out
            InvalidRequestError: If request parameters are invalid
            ProviderError: For other provider-specific errors

        Example:
            ```python
            # Simple streaming
            async for chunk in provider.generate_stream("What is Python?"):
                print(chunk, end="", flush=True)

            # With custom parameters
            params = GenerationParams(temperature=0.8, max_tokens=500)
            async for chunk in provider.generate_stream("Write a story", params=params):
                print(chunk, end="", flush=True)
            ```

        Note:
            The streaming implementation uses Server-Sent Events (SSE) format.
            The stream is parsed line-by-line, extracting JSON payloads from
            "data: {...}" lines. The stream ends when "data: [DONE]" is received.
        """
        # Ensure valid access token before making request
        await self._ensure_access_token()

        # Prepare API endpoint URL
        base_url = self.config.base_url or self.DEFAULT_BASE_URL
        url = f"{base_url}/chat/completions"

        # Prepare request headers
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/json",
        }

        # Prepare request payload (same as generate(), but with stream=True)
        payload: dict[str, Any] = {
            "model": self.config.model or self.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,  # Enable streaming
        }

        # Add optional generation parameters from params
        if params:
            if params.max_tokens:
                payload["max_tokens"] = params.max_tokens
            if params.temperature is not None:
                payload["temperature"] = params.temperature
            if params.top_p is not None:
                payload["top_p"] = params.top_p
            if params.stop:
                payload["stop"] = params.stop

        self.logger.debug(
            f"Sending streaming request to GigaChat API: model={payload['model']}, "
            f"prompt_length={len(prompt)}"
        )

        try:
            # Use streaming request instead of regular POST
            async with self._client.stream(
                "POST", url, headers=headers, json=payload
            ) as response:
                # Check for 401 BEFORE starting to read the stream
                # This allows us to retry with a fresh token
                if response.status_code == 401:
                    self.logger.warning(
                        "Token expired before streaming, refreshing and retrying..."
                    )
                    # Force token refresh by clearing current token
                    async with self._token_lock:
                        self._access_token = None
                        self._token_expires_at = None
                    # Refresh token
                    await self._ensure_access_token()
                    # Update headers with new token and new RqUID
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    headers["RqUID"] = str(uuid.uuid4())
                    # Retry streaming request ONCE
                    async with self._client.stream(
                        "POST", url, headers=headers, json=payload
                    ) as retry_response:
                        # Check status code after retry
                        if retry_response.status_code != 200:
                            self._handle_error(retry_response)
                        # Parse and yield chunks from retry response
                        async for chunk in self._parse_sse_stream(retry_response):
                            yield chunk
                    return

                # Handle other errors (before reading stream)
                if response.status_code != 200:
                    self._handle_error(response)

                # Parse and yield chunks from SSE stream
                async for chunk in self._parse_sse_stream(response):
                    yield chunk

        except httpx.TimeoutException:
            raise TimeoutError(
                f"Streaming request to GigaChat API timed out after {self.config.timeout}s"
            ) from None
        except httpx.ConnectError as e:
            raise ProviderError(f"Connection error to GigaChat API: {e}") from e
        except httpx.NetworkError as e:
            raise ProviderError(f"Network error to GigaChat API: {e}") from e
        except ProviderError:
            # Re-raise provider errors (AuthenticationError, RateLimitError, etc.)
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise ProviderError(
                f"Unexpected error during streaming generation: {e}"
            ) from e

