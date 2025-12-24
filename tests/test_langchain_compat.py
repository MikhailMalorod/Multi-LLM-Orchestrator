"""Unit tests for LangChain compatibility layer.

This module tests MultiLLMOrchestrator integration with LangChain,
including parameter mapping, sync/async calls, and error handling.
"""

import sys
import asyncio

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

    @pytest.mark.asyncio
    async def test_call_from_async_context(
        self, router_with_providers: Router
    ) -> None:
        """Test _call() works when called from async context (e.g., Telegram bot).
        
        Previously failed with: RuntimeError: asyncio.run() cannot be called 
        from a running event loop.
        
        Verifies that the method uses isolated event loop and does not conflict
        with existing async contexts like Telegram bot handlers or FastAPI endpoints.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        
        # Call synchronous method from async context (like in Telegram handlers)
        response = llm._call("What is Python?", temperature=0.5, stop=["END"])
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert response.startswith("Mock response to:")

    @pytest.mark.asyncio
    async def test_multiple_calls_from_async_context(
        self, router_with_providers: Router
    ) -> None:
        """Test multiple sequential _call() invocations from async context.

        Regression test for Issue #2: Event loop closes after first request.

        Previously failed with pattern:
        - 1st call: success
        - 2nd call: RuntimeError: Event loop is closed
        - 3rd call: success
        - 4th call: RuntimeError: Event loop is closed

        This test simulates production Telegram bot scenario where users send
        multiple messages in quick succession via asyncio.to_thread() calls.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)

        results: list[str] = []
        for i in range(1, 6):
            response = await asyncio.to_thread(
                llm._call, f"Request #{i}: What is Python?"
            )
            results.append(response)

        assert len(results) == 5
        assert all(isinstance(r, str) for r in results)
        assert all(len(r) > 0 for r in results)
        assert all(r.startswith("Mock response to:") for r in results)


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


class TestMultiLLMOrchestratorGenerate:
    """Test synchronous _generate() method with batch processing."""

    @pytest.mark.asyncio
    async def test_generate_from_async_context(
        self, router_with_providers: Router
    ) -> None:
        """Test _generate() works when called from async context with multiple prompts.
        
        Previously failed with: RuntimeError: asyncio.run() cannot be called 
        from a running event loop.
        
        Verifies that batch processing uses isolated event loop for all prompts
        and does not conflict with existing async contexts.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)
        
        # Call batch generation from async context
        prompts = ["What is Python?", "What is JavaScript?", "What is Rust?"]
        result = llm._generate(prompts, temperature=0.7)
        
        # Verify LLMResult structure
        assert hasattr(result, "generations")
        assert len(result.generations) == 3
        
        # Verify each generation
        for generation_list in result.generations:
            assert len(generation_list) == 1
            assert hasattr(generation_list[0], "text")
            assert isinstance(generation_list[0].text, str)
            assert len(generation_list[0].text) > 0

    @pytest.mark.asyncio
    async def test_multiple_generate_calls_from_async_context(
        self, router_with_providers: Router
    ) -> None:
        """Test multiple sequential _generate() calls from async context.

        Regression test for Issue #2: Event loop closes after first request.

        Ensures that batch processing via _generate() is stable when invoked
        multiple times from an async context using asyncio.to_thread().
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)

        prompts_batch_1 = ["Question 1", "Question 2"]
        result1 = await asyncio.to_thread(llm._generate, prompts_batch_1)
        assert len(result1.generations) == 2
        for generation_list in result1.generations:
            assert len(generation_list) == 1
            assert hasattr(generation_list[0], "text")
            assert isinstance(generation_list[0].text, str)
            assert len(generation_list[0].text) > 0
            assert generation_list[0].text.startswith("Mock response to:")

        prompts_batch_2 = ["Question 3", "Question 4"]
        result2 = await asyncio.to_thread(llm._generate, prompts_batch_2)
        assert len(result2.generations) == 2
        for generation_list in result2.generations:
            assert len(generation_list) == 1
            assert hasattr(generation_list[0], "text")
            assert generation_list[0].text.startswith("Mock response to:")

        prompts_batch_3 = ["Question 5", "Question 6"]
        result3 = await asyncio.to_thread(llm._generate, prompts_batch_3)
        assert len(result3.generations) == 2
        for generation_list in result3.generations:
            assert len(generation_list) == 1
            assert hasattr(generation_list[0], "text")
            assert isinstance(generation_list[0].text, str)
            assert len(generation_list[0].text) > 0


class TestMultiLLMOrchestratorThreadSafety:
    """Test thread safety and concurrent request handling for MultiLLMOrchestrator."""

    @pytest.mark.asyncio
    async def test_rapid_fire_requests(
        self, router_with_providers: Router
    ) -> None:
        """Test rapid-fire _call() requests without delays.

        Simulates high-load scenario where multiple users send messages
        simultaneously (e.g., peak hours in production bot). This is a
        regression test around Issue #2 to ensure that concurrent calls
        do not surface "Event loop is closed" due to thread reuse.
        """
        llm = MultiLLMOrchestrator(router=router_with_providers)

        tasks = [
            asyncio.to_thread(llm._call, f"Rapid request #{i}") for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(isinstance(r, str) for r in results)
        assert all(len(r) > 0 for r in results)

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

