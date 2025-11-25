"""Ollama provider implementation for Multi-LLM Orchestrator.

This module integrates local Ollama deployments via their HTTP API. Ollama is
designed for running open-source LLMs (Llama 3, Mistral, Phi, etc.) locally
with an API that mirrors cloud experiences while keeping data on-device.
"""

from __future__ import annotations

from typing import Any, cast

import httpx

from .base import (
    BaseProvider,
    GenerationParams,
    InvalidRequestError,
    ProviderConfig,
    ProviderError,
    TimeoutError,
)


class OllamaProvider(BaseProvider):
    """Provider implementation for running local LLMs via Ollama.

    Ollama exposes a REST API (default: http://localhost:11434) for interacting
    with locally hosted models. This provider wraps the `/api/generate`
    endpoint for single-turn generations and `/api/tags` for health checks.

    Example:
        ```python
        config = ProviderConfig(
            name="ollama",
            model="llama3",
            base_url="http://localhost:11434",
        )
        provider = OllamaProvider(config)
        response = await provider.generate("Why is the sky blue?")
        ```
    """

    DEFAULT_BASE_URL = "http://localhost:11434"
    GENERATE_ENDPOINT = "/api/generate"
    TAGS_ENDPOINT = "/api/tags"

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize provider with required configuration."""
        super().__init__(config)

        if not config.model:
            raise ValueError("model is required for OllamaProvider")

        self._base_url = config.base_url or self.DEFAULT_BASE_URL
        self._client = httpx.AsyncClient(
            timeout=config.timeout,
            verify=config.verify_ssl,
        )

        self.logger.info(
            "OllamaProvider initialized: model=%s base_url=%s",
            self.config.model,
            self._base_url,
        )

    async def generate(
        self,
        prompt: str,
        params: GenerationParams | None = None,
    ) -> str:
        """Generate text using Ollama `/api/generate` endpoint.

        Args:
            prompt: User instruction to send to the local model.
            params: Optional sampling parameters to forward via Ollama options.

        Returns:
            Generated completion text from the selected model.

        Raises:
            InvalidRequestError: If the requested model is not available locally.
            ProviderError: For server errors, network issues, or malformed responses.
            TimeoutError: When Ollama does not respond within configured timeout.
        """
        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
        }

        options: dict[str, Any] = {}
        if params:
            # Map GenerationParams to Ollama options while renaming fields
            if params.temperature is not None:
                options["temperature"] = params.temperature
            if params.max_tokens:
                options["num_predict"] = params.max_tokens
            if params.top_p is not None:
                options["top_p"] = params.top_p

        if options:
            payload["options"] = options

        url = f"{self._base_url}{self.GENERATE_ENDPOINT}"
        self.logger.debug(
            "Sending request to Ollama: model=%s prompt_length=%d options=%s",
            payload["model"],
            len(prompt),
            list(options.keys()),
        )

        try:
            response = await self._client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Request to Ollama timed out after {self.config.timeout}s"
            ) from exc
        except httpx.ConnectError as exc:
            raise ProviderError(
                f"Cannot connect to Ollama at {self._base_url}. Is Ollama running?"
            ) from exc
        except httpx.NetworkError as exc:
            raise ProviderError(f"Network error while calling Ollama: {exc}") from exc

        if response.status_code == 404:
            raise InvalidRequestError(
                f"Model '{self.config.model}' not found in Ollama"
            )
        if response.status_code >= 500:
            raise ProviderError(
                f"Ollama server error: HTTP {response.status_code}"
            )
        if response.status_code != 200:
            raise ProviderError(
                f"Unexpected status from Ollama: HTTP {response.status_code}"
            )

        try:
            data: dict[str, Any] = cast(dict[str, Any], response.json())
            completion: str = cast(str, data["response"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Invalid response format from Ollama API") from exc

        self.logger.debug("Received Ollama response (%d chars)", len(completion))
        return completion

    async def health_check(self) -> bool:
        """Verify Ollama availability via `/api/tags` endpoint.

        Returns:
            True if Ollama responds with HTTP 200, False otherwise.
        """
        url = f"{self._base_url}{self.TAGS_ENDPOINT}"

        try:
            response = await self._client.get(
                url,
                timeout=httpx.Timeout(5.0, connect=5.0),
            )
        except httpx.HTTPError as exc:
            self.logger.warning("Ollama health check failed: %s", exc)
            return False

        is_healthy = response.status_code == 200
        if not is_healthy:
            self.logger.warning(
                "Ollama health check returned status %s",
                response.status_code,
            )
        return is_healthy


