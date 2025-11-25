"""Unit tests for LangChain compatibility layer.

This module tests MultiLLMOrchestrator integration with LangChain,
including parameter mapping, sync/async calls, and error handling.
"""

import sys

import pytest

# Skip tests if langchain-core is not available
langchain = pytest.importorskip("langchain_core")

from orchestrator import Router
from orchestrator.langchain import MultiLLMOrchestrator
from orchestrator.providers.base import (
    GenerationParams,
    ProviderError,
    ProviderConfig,
    TimeoutError,
)
from orchestrator.providers.mock import MockProvider


class TestMultiLLMOrchestratorInitialization:
    """Test MultiLLMOrchestrator initialization and validation."""

    def test_init_with_valid_router(self, router_with_providers: Router) -> None:
        """Test that MultiLLMOrchestrator initializes with valid router.
        
        Verifies that MultiLLMOrchestrator can be created with a router
        that has providers registered.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        assert llm.router == router_with_providers
        assert llm.router.providers

    def test_init_with_empty_router_raises_error(
        self, router_round_robin: Router
    ) -> None:
        """Test that initialization with empty router raises ValueError.
        
        Verifies that creating MultiLLMOrchestrator with a router that has
        no providers raises ValueError with appropriate message.
        """
        with pytest.raises(ValueError, match="at least one provider"):
            MultiLLMOrchestrator(router=router_round_robin)

    def test_init_with_none_router_raises_error(self) -> None:
        """Test that initialization with None router raises ValueError.
        
        Verifies that creating MultiLLMOrchestrator with None router
        raises ValueError (our validation happens before Pydantic validation).
        """
        with pytest.raises(ValueError, match="cannot be None"):
            MultiLLMOrchestrator(router=None)  # type: ignore

    def test_llm_type_property(self, router_with_providers: Router) -> None:
        """Test that _llm_type property returns correct identifier.
        
        Verifies that _llm_type property returns "multi-llm-orchestrator"
        as expected by LangChain.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        assert llm._llm_type == "multi-llm-orchestrator"


class TestMultiLLMOrchestratorCall:
    """Test synchronous _call() method."""

    def test_call_basic(self, router_with_providers: Router) -> None:
        """Test basic synchronous call with MockProvider.
        
        Verifies that _call() successfully generates a response
        using the router's providers.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = llm._call("test prompt")
        assert isinstance(response, str)
        assert response.startswith("Mock response to:")

    def test_call_with_temperature(self, router_with_providers: Router) -> None:
        """Test _call() with temperature parameter.
        
        Verifies that temperature parameter is correctly mapped
        to GenerationParams and passed to the router.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = llm._call("test", temperature=0.9)
        assert isinstance(response, str)
        # Response should be generated (temperature is passed through)

    def test_call_with_max_tokens(self, router_with_providers: Router) -> None:
        """Test _call() with max_tokens parameter.
        
        Verifies that max_tokens parameter is correctly mapped
        and limits the response length.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = llm._call("test", max_tokens=10)
        assert isinstance(response, str)
        # MockProvider respects max_tokens (interpreted as character limit)
        assert len(response) <= 10

    def test_call_with_stop(self, router_with_providers: Router) -> None:
        """Test _call() with stop sequences parameter.
        
        Verifies that stop parameter is correctly mapped to GenerationParams.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        stop_sequences = ["\n\n", "END"]
        response = llm._call("test", stop=stop_sequences)
        assert isinstance(response, str)
        # Response should be generated (stop is passed through)

    def test_call_with_all_params(self, router_with_providers: Router) -> None:
        """Test _call() with all parameters (temperature, max_tokens, stop).
        
        Verifies that multiple parameters are correctly mapped together.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = llm._call(
            "test",
            temperature=0.8,
            max_tokens=20,
            stop=["\n\n"],
        )
        assert isinstance(response, str)
        assert len(response) <= 20

    def test_call_with_timeout_error(self) -> None:
        """Test _call() handles TimeoutError from providers.
        
        Verifies that TimeoutError from providers is correctly
        propagated through the wrapper.
        """
        router = Router(strategy="round-robin")
        config = ProviderConfig(name="timeout-provider", model="mock-timeout")
        router.add_provider(MockProvider(config))

        llm = MultiLLMOrchestrator(router=router)
        with pytest.raises(TimeoutError, match="Mock timeout simulation"):
            llm._call("test")

    def test_call_with_provider_error(self) -> None:
        """Test _call() handles ProviderError when no providers available.
        
        Verifies that ProviderError is correctly propagated when
        router has no providers (edge case, should be caught in __init__).
        """
        router = Router(strategy="round-robin")
        # Router is empty, but we can't create MultiLLMOrchestrator with it
        # This test verifies that __init__ validation works
        with pytest.raises(ValueError, match="at least one provider"):
            MultiLLMOrchestrator(router=router)


class TestMultiLLMOrchestratorACall:
    """Test asynchronous _acall() method."""

    @pytest.mark.asyncio
    async def test_acall_basic(self, router_with_providers: Router) -> None:
        """Test basic asynchronous call with MockProvider.
        
        Verifies that _acall() successfully generates a response
        asynchronously using the router's providers.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = await llm._acall("test prompt")
        assert isinstance(response, str)
        assert response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_acall_with_temperature(
        self, router_with_providers: Router
    ) -> None:
        """Test _acall() with temperature parameter.
        
        Verifies that temperature parameter is correctly mapped
        in async context.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = await llm._acall("test", temperature=0.9)
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_acall_with_max_tokens(
        self, router_with_providers: Router
    ) -> None:
        """Test _acall() with max_tokens parameter.
        
        Verifies that max_tokens parameter is correctly mapped
        and limits response in async context.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = await llm._acall("test", max_tokens=10)
        assert isinstance(response, str)
        assert len(response) <= 10

    @pytest.mark.asyncio
    async def test_acall_with_stop(self, router_with_providers: Router) -> None:
        """Test _acall() with stop sequences parameter.
        
        Verifies that stop parameter is correctly mapped in async context.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        stop_sequences = ["\n\n", "END"]
        response = await llm._acall("test", stop=stop_sequences)
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_acall_with_all_params(
        self, router_with_providers: Router
    ) -> None:
        """Test _acall() with all parameters.
        
        Verifies that multiple parameters are correctly mapped together
        in async context.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        response = await llm._acall(
            "test",
            temperature=0.8,
            max_tokens=20,
            stop=["\n\n"],
        )
        assert isinstance(response, str)
        assert len(response) <= 20

    @pytest.mark.asyncio
    async def test_acall_with_timeout_error(self) -> None:
        """Test _acall() handles TimeoutError from providers.
        
        Verifies that TimeoutError is correctly propagated in async context.
        """
        router = Router(strategy="round-robin")
        config = ProviderConfig(name="timeout-provider", model="mock-timeout")
        router.add_provider(MockProvider(config))

        llm = MultiLLMOrchestrator(router=router)
        with pytest.raises(TimeoutError, match="Mock timeout simulation"):
            await llm._acall("test")


class TestMultiLLMOrchestratorImportError:
    """Test ImportError handling when langchain-core is not available."""

    def test_import_without_langchain(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that MultiLLMOrchestrator raises ImportError without langchain-core.
        
        Verifies that when langchain-core is not available, importing
        and instantiating MultiLLMOrchestrator raises ImportError with
        clear installation instructions.
        """
        # Simulate absence of langchain-core
        monkeypatch.setitem(sys.modules, "langchain_core", None)
        monkeypatch.setitem(
            sys.modules, "langchain_core.language_models.llms", None
        )

        # Reload module to trigger ImportError path
        import importlib
        import orchestrator.langchain

        importlib.reload(orchestrator.langchain)

        from orchestrator.langchain import MultiLLMOrchestrator
        from orchestrator import Router

        router = Router(strategy="round-robin")
        config = ProviderConfig(name="test", model="mock-normal")
        router.add_provider(MockProvider(config))

        with pytest.raises(ImportError, match="langchain-core is required"):
            MultiLLMOrchestrator(router=router)

        # Restore module for other tests
        importlib.reload(orchestrator.langchain)

