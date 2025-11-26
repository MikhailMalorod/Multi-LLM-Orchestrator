"""LangChain compatibility layer for Multi-LLM Orchestrator.

This module provides a LangChain-compatible wrapper for the Multi-LLM Orchestrator,
allowing users to use our Router and providers with LangChain chains, prompts,
and other LangChain components.

The module uses optional dependency pattern - langchain-core must be installed
via: pip install multi-llm-orchestrator[langchain]

Example:
    ```python
    from langchain_core.prompts import ChatPromptTemplate
    from orchestrator.langchain import MultiLLMOrchestrator
    from orchestrator import Router
    from orchestrator.providers import GigaChatProvider, ProviderConfig

    # Create router with providers
    router = Router(strategy="round-robin")
    config = ProviderConfig(
        name="gigachat",
        api_key="key",
        model="GigaChat"
    )
    router.add_provider(GigaChatProvider(config))

    # Use as LangChain LLM
    llm = MultiLLMOrchestrator(router=router)

    # Work with LangChain chains
    prompt = ChatPromptTemplate.from_template("Tell me about {topic}")
    chain = prompt | llm
    response = chain.invoke({"topic": "Python"})
    ```
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from pydantic import Field

from .providers.base import GenerationParams
from .router import Router

# Conditional import for langchain-core
try:
    from langchain_core.language_models.llms import BaseLLM
    from langchain_core.outputs import Generation, LLMResult

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Dummy base class for type hints when langchain-core is not available
    class BaseLLM:  # type: ignore
        """Dummy BaseLLM class when langchain-core is not installed."""

        pass

    # Dummy types for type hints
    LLMResult = Any  # type: ignore
    Generation = Any  # type: ignore


if LANGCHAIN_AVAILABLE:

    class MultiLLMOrchestrator(BaseLLM):
        """LangChain-compatible wrapper for Multi-LLM Orchestrator Router.

        This class allows using Multi-LLM Orchestrator Router and providers
        with LangChain chains, prompts, and other LangChain components.

        The wrapper implements the BaseLLM interface from LangChain, providing
        both synchronous and asynchronous text generation methods.

        Attributes:
            router: Router instance for managing LLM provider selection and routing

        Example:
            ```python
            from orchestrator.langchain import MultiLLMOrchestrator
            from orchestrator import Router
            from orchestrator.providers import MockProvider, ProviderConfig

            # Create router with providers
            router = Router(strategy="round-robin")
            config = ProviderConfig(name="mock", model="mock-normal")
            router.add_provider(MockProvider(config))

            # Use as LangChain LLM
            llm = MultiLLMOrchestrator(router=router)

            # Synchronous call
            response = llm.invoke("What is Python?")

            # Use in LangChain chain
            from langchain_core.prompts import ChatPromptTemplate
            prompt = ChatPromptTemplate.from_template("Tell me about {topic}")
            chain = prompt | llm
            result = chain.invoke({"topic": "Python"})
            ```
        """

        router: Router = Field(
            ...,
            description="Router instance for managing LLM provider selection and routing"
        )

        def __init__(self, router: Router, **kwargs: Any) -> None:
            """Initialize MultiLLMOrchestrator with a Router instance.

            Args:
                router: Router instance containing configured providers.
                       Must have at least one provider registered.
                **kwargs: Additional arguments passed to BaseLLM

            Raises:
                ValueError: If router is None or has no providers registered
            """
            if router is None:
                raise ValueError("Router cannot be None")
            if not router.providers:
                raise ValueError(
                    "Router must have at least one provider registered. "
                    "Use router.add_provider() to add providers."
                )
            # Pass router to super().__init__ for Pydantic validation
            # BaseLLM doesn't accept router in signature, but Pydantic model requires it
            super().__init__(router=router, **kwargs)  # type: ignore[call-arg]

        @property
        def _llm_type(self) -> str:
            """Return identifier for this LLM type.

            Returns:
                String identifier "multi-llm-orchestrator" for LangChain
            """
            return "multi-llm-orchestrator"

        def _map_params(
            self, stop: list[str] | None = None, **kwargs: Any
        ) -> GenerationParams:
            """Map LangChain parameters to GenerationParams.

            Only includes parameters that are explicitly provided (not None).
            Uses GenerationParams defaults for missing parameters.

            Args:
                stop: Optional list of stop sequences from LangChain
                **kwargs: Additional parameters from LangChain (temperature, max_tokens, etc.)

            Returns:
                GenerationParams instance with mapped parameters
            """
            params_dict: dict[str, Any] = {}

            # Only add temperature if explicitly provided
            if "temperature" in kwargs and kwargs["temperature"] is not None:
                params_dict["temperature"] = kwargs["temperature"]

            # Only add max_tokens if explicitly provided
            if "max_tokens" in kwargs and kwargs["max_tokens"] is not None:
                params_dict["max_tokens"] = kwargs["max_tokens"]

            # Handle stop parameter (from argument or kwargs)
            if stop is not None:
                params_dict["stop"] = stop
            elif "stop" in kwargs and kwargs["stop"] is not None:
                params_dict["stop"] = kwargs["stop"]

            # GenerationParams will use defaults for missing parameters
            return GenerationParams(**params_dict)

        def _generate(
            self,
            prompts: list[str],
            stop: list[str] | None = None,
            run_manager: Any = None,
            **kwargs: Any,
        ) -> Any:
            """Generate text completions for a list of prompts.

            This method is called by LangChain for batch text generation.
            It processes each prompt individually and returns a list of results.

            Args:
                prompts: List of input text prompts to generate completions for
                stop: Optional list of stop sequences that will stop generation
                **kwargs: Additional generation parameters (temperature, max_tokens, etc.)

            Returns:
                LLMResult object containing generated text responses

            Raises:
                ProviderError: If no providers are registered or all providers fail
                TimeoutError: If all providers timeout
                RateLimitError: If all providers hit rate limit
                AuthenticationError: If all providers fail authentication
                InvalidRequestError: If all providers receive invalid requests
            """
            # Map parameters (uses defaults from GenerationParams for missing params)
            params = self._map_params(stop, **kwargs)
            # Process each prompt
            generations = []
            for prompt in prompts:
                # Call router.route() through asyncio.run() (creates isolated event loop)
                text = asyncio.run(self.router.route(prompt, params=params))
                generations.append([Generation(text=text)])
            return LLMResult(generations=generations)

        def _call(
            self, prompt: str, stop: list[str] | None = None, **kwargs: Any
        ) -> str:
            """Generate text completion synchronously.

            This method is called by LangChain for synchronous text generation.
            It maps LangChain parameters to GenerationParams and calls the
            Router's route method through asyncio.run().

            Args:
                prompt: Input text prompt to generate completion for
                stop: Optional list of stop sequences that will stop generation
                **kwargs: Additional generation parameters (temperature, max_tokens, etc.)

            Returns:
                Generated text response from the Router

            Raises:
                ProviderError: If no providers are registered or all providers fail
                TimeoutError: If all providers timeout
                RateLimitError: If all providers hit rate limit
                AuthenticationError: If all providers fail authentication
                InvalidRequestError: If all providers receive invalid requests
            """
            # Map parameters (uses defaults from GenerationParams for missing params)
            params = self._map_params(stop, **kwargs)
            # Call router.route() through asyncio.run() (creates isolated event loop)
            return asyncio.run(self.router.route(prompt, params=params))

        async def _acall(
            self, prompt: str, stop: list[str] | None = None, **kwargs: Any
        ) -> str:
            """Generate text completion asynchronously.

            This method is called by LangChain for asynchronous text generation.
            It maps LangChain parameters to GenerationParams and directly calls
            the Router's async route method.

            Args:
                prompt: Input text prompt to generate completion for
                stop: Optional list of stop sequences that will stop generation
                **kwargs: Additional generation parameters (temperature, max_tokens, etc.)

            Returns:
                Generated text response from the Router

            Raises:
                ProviderError: If no providers are registered or all providers fail
                TimeoutError: If all providers timeout
                RateLimitError: If all providers hit rate limit
                AuthenticationError: If all providers fail authentication
                InvalidRequestError: If all providers receive invalid requests
            """
            # Map parameters (uses defaults from GenerationParams for missing params)
            params = self._map_params(stop, **kwargs)
            # Direct async call to router.route()
            return await self.router.route(prompt, params=params)

        async def _astream(  # type: ignore[override]
            self,
            prompt: str,
            stop: list[str] | None = None,
            run_manager: Any = None,
            **kwargs: Any,
        ) -> AsyncIterator[str]:
            """Stream text completion asynchronously.

            This method is called by LangChain for asynchronous streaming text generation.
            It maps LangChain parameters to GenerationParams and streams chunks
            directly from the Router's route_stream method.

            Args:
                prompt: Input text prompt to generate completion for
                stop: Optional list of stop sequences that will stop generation
                **kwargs: Additional generation parameters (temperature, max_tokens, etc.)

            Yields:
                Chunks of generated text as they become available from the Router

            Raises:
                ProviderError: If no providers are registered or all providers fail
                TimeoutError: If all providers timeout
                RateLimitError: If all providers hit rate limit
                AuthenticationError: If all providers fail authentication
                InvalidRequestError: If all providers receive invalid requests

            Example:
                ```python
                async for chunk in llm._astream("What is Python?"):
                    print(chunk, end="", flush=True)
                ```
            """
            # Map parameters (uses defaults from GenerationParams for missing params)
            params = self._map_params(stop, **kwargs)
            # Stream directly from router.route_stream()
            async for chunk in self.router.route_stream(prompt, params=params):
                yield chunk

        def _stream(  # type: ignore[override]
            self,
            prompt: str,
            stop: list[str] | None = None,
            run_manager: Any = None,
            **kwargs: Any,
        ) -> Iterator[str]:
            """Stream text completion synchronously.

            This method is called by LangChain for synchronous streaming text generation.
            It maps LangChain parameters to GenerationParams and converts the async
            streaming generator from router.route_stream() into a synchronous iterator.

            The conversion is done by creating a dedicated event loop and using
            run_until_complete() to fetch chunks from the async generator. This approach
            is consistent with the pattern used in _call() and _generate() methods.

            Args:
                prompt: Input text prompt to generate completion for
                stop: Optional list of stop sequences that will stop generation
                **kwargs: Additional generation parameters (temperature, max_tokens, etc.)

            Yields:
                Chunks of generated text as they become available from the Router

            Raises:
                ProviderError: If no providers are registered or all providers fail
                TimeoutError: If all providers timeout
                RateLimitError: If all providers hit rate limit
                AuthenticationError: If all providers fail authentication
                InvalidRequestError: If all providers receive invalid requests

            Example:
                ```python
                for chunk in llm._stream("What is Python?"):
                    print(chunk, end="", flush=True)
                ```

            Note:
                This method creates a new event loop for streaming, which is safe
                for use in synchronous contexts (like LangChain's sync API). However,
                it should not be called from within an existing async context.
            """
            # Map parameters (uses defaults from GenerationParams for missing params)
            params = self._map_params(stop, **kwargs)

            # Create a dedicated event loop for streaming
            # This is consistent with _call() and _generate() which use asyncio.run()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Get async generator from router
                async_gen = self.router.route_stream(prompt, params=params)

                # Convert async generator to sync iterator
                while True:
                    try:
                        # Fetch next chunk from async generator
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        # Generator exhausted, exit loop
                        break
            finally:
                # Always close the event loop to clean up resources
                loop.close()

else:

    class MultiLLMOrchestrator:  # type: ignore
        """Dummy MultiLLMOrchestrator class when langchain-core is not installed.

        Raises ImportError when instantiated to provide clear error message.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Raise ImportError with installation instructions.

            Raises:
                ImportError: Always raised with instructions to install langchain-core
            """
            raise ImportError(
                "langchain-core is required for LangChain integration. "
                "Install with: pip install multi-llm-orchestrator[langchain]"
            )

