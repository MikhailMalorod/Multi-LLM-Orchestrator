"""Unit tests for OllamaProvider."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from pytest_httpx import HTTPXMock

from orchestrator.providers import (
    GenerationParams,
    InvalidRequestError,
    OllamaProvider,
    ProviderConfig,
    ProviderError,
    TimeoutError,
)

OLLAMA_URL = "http://localhost:11434"
GENERATE_URL = f"{OLLAMA_URL}/api/generate"
TAGS_URL = f"{OLLAMA_URL}/api/tags"


class TestOllamaProviderConfig:
    """Configuration validation tests."""

    def test_ollama_provider_creation_with_model(self) -> None:
        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert provider.config.model == "llama3"

    def test_ollama_provider_creation_without_model(self) -> None:
        config = ProviderConfig(name="ollama", model=None)

        with pytest.raises(ValueError, match="model is required"):
            OllamaProvider(config)

    def test_ollama_provider_custom_base_url(self) -> None:
        custom_url = "http://127.0.0.1:9000"
        config = ProviderConfig(name="ollama", model="llama3", base_url=custom_url)
        provider = OllamaProvider(config)

        assert provider._base_url == custom_url  # noqa: SLF001 (validated for config)


class TestOllamaParameterMapping:
    """Ensure GenerationParams are properly mapped to options."""

    @pytest.mark.asyncio
    async def test_parameter_mapping_temperature(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        captured_payload: dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_payload.update(json.loads(request.content))
            return httpx.Response(200, json={"model": "llama3", "response": "ok"})

        httpx_mock.add_callback(_capture, method="POST", url=GENERATE_URL)

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)
        params = GenerationParams(temperature=0.42)

        await provider.generate("test", params=params)

        assert captured_payload["options"]["temperature"] == 0.42

    @pytest.mark.asyncio
    async def test_parameter_mapping_max_tokens(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        captured_payload: dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_payload.update(json.loads(request.content))
            return httpx.Response(200, json={"model": "llama3", "response": "ok"})

        httpx_mock.add_callback(_capture, method="POST", url=GENERATE_URL)

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)
        params = GenerationParams(max_tokens=256)

        await provider.generate("test", params=params)

        assert captured_payload["options"]["num_predict"] == 256

    @pytest.mark.asyncio
    async def test_parameter_mapping_top_p(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        captured_payload: dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_payload.update(json.loads(request.content))
            return httpx.Response(200, json={"model": "llama3", "response": "ok"})

        httpx_mock.add_callback(_capture, method="POST", url=GENERATE_URL)

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)
        params = GenerationParams(top_p=0.5)

        await provider.generate("test", params=params)

        assert captured_payload["options"]["top_p"] == 0.5

    @pytest.mark.asyncio
    async def test_parameter_mapping_ignore_stop(
        self,
        httpx_mock: HTTPXMock,
    ) -> None:
        captured_payload: dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_payload.update(json.loads(request.content))
            return httpx.Response(200, json={"model": "llama3", "response": "ok"})

        httpx_mock.add_callback(_capture, method="POST", url=GENERATE_URL)

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)
        params = GenerationParams(stop=["END"])

        await provider.generate("test", params=params)

        assert "options" not in captured_payload or "stop" not in (
            captured_payload.get("options") or {}
        )


class TestOllamaGenerateSuccess:
    """Successful generation scenarios."""

    @pytest.mark.asyncio
    async def test_generate_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=GENERATE_URL,
            json={"model": "llama3", "response": "Because molecules scatter blue light."},
        )

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        result = await provider.generate("Why is the sky blue?")

        assert result.startswith("Because")

    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=GENERATE_URL,
            json={"model": "llama3", "response": "Parametrized answer"},
        )

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)
        params = GenerationParams(temperature=0.1, max_tokens=64, top_p=0.9)

        response = await provider.generate("test", params=params)

        assert response == "Parametrized answer"

    @pytest.mark.asyncio
    async def test_generate_without_parameters(self, httpx_mock: HTTPXMock) -> None:
        captured_payload: dict[str, Any] = {}

        def _capture(request: httpx.Request) -> httpx.Response:
            captured_payload.update(json.loads(request.content))
            return httpx.Response(200, json={"model": "llama3", "response": "No params"})

        httpx_mock.add_callback(_capture, method="POST", url=GENERATE_URL)

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        response = await provider.generate("test")

        assert response == "No params"
        assert "options" not in captured_payload


class TestOllamaGenerateErrors:
    """Error handling for Ollama generate endpoint."""

    @pytest.mark.asyncio
    async def test_generate_model_not_found(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=GENERATE_URL,
            status_code=404,
            json={"error": "model not found"},
        )

        config = ProviderConfig(name="ollama", model="missing-model")
        provider = OllamaProvider(config)

        with pytest.raises(InvalidRequestError, match="missing-model"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_generate_server_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=GENERATE_URL,
            status_code=500,
            json={"error": "internal error"},
        )

        config = ProviderConfig(name="ollama", model="llama3")

        provider = OllamaProvider(config)

        with pytest.raises(ProviderError, match="server error"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_exception(
            exception=httpx.ConnectError("connection refused"),
            method="POST",
            url=GENERATE_URL,
        )

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(ProviderError, match="Cannot connect to Ollama"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_generate_timeout(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_exception(
            exception=httpx.TimeoutException("timed out"),
            method="POST",
            url=GENERATE_URL,
        )

        config = ProviderConfig(name="ollama", model="llama3", timeout=5)
        provider = OllamaProvider(config)

        with pytest.raises(TimeoutError, match="timed out after 5"):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_generate_invalid_response(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="POST",
            url=GENERATE_URL,
            json={"model": "llama3"},
        )

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        with pytest.raises(ProviderError, match="Invalid response format"):
            await provider.generate("test")


class TestOllamaHealthCheck:
    """Health check coverage."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=TAGS_URL,
            status_code=200,
            json={"models": []},
        )

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_response(
            method="GET",
            url=TAGS_URL,
            status_code=500,
            json={"error": "server down"},
        )

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, httpx_mock: HTTPXMock) -> None:
        httpx_mock.add_exception(
            exception=httpx.ConnectError("connection refused"),
            method="GET",
            url=TAGS_URL,
        )

        config = ProviderConfig(name="ollama", model="llama3")
        provider = OllamaProvider(config)

        assert await provider.health_check() is False

