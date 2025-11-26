# Multi-LLM Orchestrator

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PyPI](https://img.shields.io/pypi/v/multi-llm-orchestrator.svg)
![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)
![Tests](https://img.shields.io/badge/tests-117%20passed-success.svg)

A unified interface for orchestrating multiple Large Language Model providers with intelligent routing and fallback mechanisms.

## Overview

The Multi-LLM Orchestrator provides a seamless way to integrate and manage multiple LLM providers through a single, consistent interface. It supports intelligent routing strategies, automatic fallbacks, and provider-specific optimizations. Currently focused on Russian LLM providers (GigaChat, YandexGPT) with a flexible architecture that supports any LLM provider implementation.

## Quickstart

Get started with Multi-LLM Orchestrator in minutes:

### Using MockProvider (Testing)

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider

async def main():
    # Initialize router with round-robin strategy
    router = Router(strategy="round-robin")
    
    # Add providers
    for i in range(3):
        config = ProviderConfig(name=f"provider-{i+1}", model="mock-normal")
        router.add_provider(MockProvider(config))
    
    # Make a request
    response = await router.route("What is Python?")
    print(response)
    # Output: Mock response to: What is Python?

if __name__ == "__main__":
    asyncio.run(main())
```

### Using GigaChatProvider (Production)

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, GigaChatProvider

async def main():
    # Create GigaChat provider
    config = ProviderConfig(
        name="gigachat",
        api_key="your_authorization_key_here",  # OAuth2 authorization key
        model="GigaChat",  # or "GigaChat-Pro", "GigaChat-Plus"
        scope="GIGACHAT_API_PERS"  # or "GIGACHAT_API_CORP" for corporate
    )
    provider = GigaChatProvider(config)
    
    # Use with router
    router = Router(strategy="round-robin")
    router.add_provider(provider)
    
    # Generate response
    response = await router.route("What is Python?")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### Disabling SSL Verification (for self-signed certificates)

If you encounter SSL certificate errors with GigaChat (Russian CA certificates), you can disable verification:

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig

async def main():
    router = Router(strategy="round-robin")
    
    # WARNING: Disabling SSL verification is insecure
    # Use only in development or with trusted networks
    config = ProviderConfig(
        name="gigachat",
        api_key="your_authorization_key_here",
        scope="GIGACHAT_API_PERS",
        verify_ssl=False  # Disable SSL verification
    )
    
    router.add_provider(GigaChatProvider(config))
    
    response = await router.route("Hello!")
    print(response)

asyncio.run(main())
```

**⚠️ Security Warning:** Disabling SSL verification makes your application vulnerable to man-in-the-middle attacks. Use this option only in development or when working with known self-signed certificates.

### Using YandexGPTProvider (Production)

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, YandexGPTProvider

async def main():
    # Create YandexGPT provider
    config = ProviderConfig(
        name="yandexgpt",
        api_key="your_iam_token_here",  # IAM token (valid for 12 hours)
        folder_id="your_folder_id_here",  # Yandex Cloud folder ID
        model="yandexgpt/latest"  # or "yandexgpt-lite/latest"
    )
    provider = YandexGPTProvider(config)
    
    # Use with router
    router = Router(strategy="round-robin")
    router.add_provider(provider)
    
    # Generate response
    response = await router.route("What is Python?")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

### Local Models with Ollama

Run open-source LLMs locally without API keys:

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import OllamaProvider, ProviderConfig

async def main():
    router = Router(strategy="first-available")

    ollama_config = ProviderConfig(
        name="ollama",
        model="llama3",  # or "mistral", "phi", etc.
        base_url="http://localhost:11434",  # optional; defaults to localhost
    )
    router.add_provider(OllamaProvider(ollama_config))

    response = await router.route("Why is the sky blue?")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

**Requirements:** Install Ollama from <https://ollama.ai> and pull a model (e.g., `ollama pull llama3`).

The MockProvider simulates LLM behavior without requiring API credentials, while GigaChatProvider and YandexGPTProvider provide full integration with their respective APIs.

## Installation

**Requirements:**

- Python 3.11+
- Poetry (recommended) or pip

### Using Poetry

```bash
# Clone the repository
git clone https://github.com/MikhailMalorod/Multi-LLM-Orchestrator.git
cd Multi-LLM-Orchestrator

# Install dependencies
poetry install
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/MikhailMalorod/Multi-LLM-Orchestrator.git
cd Multi-LLM-Orchestrator

# Install in development mode
pip install -e .
```

## Architecture

The Multi-LLM Orchestrator follows a modular architecture with clear separation of concerns:

```
┌──────────────────────────────────────────────┐
│              User Application                │
└─────────────────┬────────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │     Router     │ ◄── Strategy: round-robin/random/first-available
         └────────┬───────┘
                  │
      ┌───────────┼───────────┐
      ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│Provider 1│ │Provider 2│ │Provider 3│
│(Base)    │ │(Base)    │ │(Base)    │
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     ▼            ▼            ▼
   (API)        (API)        (API)
```

### Components

- **Router** (`src/orchestrator/router.py`): Manages provider selection based on routing strategy and handles automatic fallback when providers fail.

- **BaseProvider** (`src/orchestrator/providers/base.py`): Abstract base class defining the interface that all provider implementations must follow. Includes configuration models (`ProviderConfig`, `GenerationParams`) and exception hierarchy.

- **MockProvider** (`src/orchestrator/providers/mock.py`): Test implementation that simulates LLM behavior without making actual API calls. Supports various simulation modes for testing different scenarios.

- **Config** (`src/orchestrator/config.py`): Future component for loading configuration from environment variables. Currently used for planned real provider integrations (GigaChat, YandexGPT).

## Routing Strategies

The Router supports three routing strategies, each suitable for different use cases:

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **round-robin** | Cycles through providers in a fixed order | Equal load distribution (recommended for production) |
| **random** | Selects a random provider from available providers | Simple random selection for load balancing |
| **first-available** | Selects the first healthy provider based on health checks | High availability scenarios with automatic unhealthy provider skipping |

The strategy is selected when initializing the Router:

```python
router = Router(strategy="round-robin")  # or "random" or "first-available"
```

## Run the Demo

See the routing strategies and fallback mechanisms in action:

```bash
python examples/routing_demo.py
```

**No API keys required** — uses MockProvider for demonstration.

The demo showcases:
- All three routing strategies (round-robin, random, first-available)
- Automatic fallback mechanism when providers fail
- Error handling when all providers are unavailable

See [routing_demo.py](examples/routing_demo.py) for the complete interactive demonstration.

## MockProvider Modes

MockProvider simulates various LLM behaviors for testing without requiring API credentials:

- **`mock-normal`** — Returns successful responses with a small delay
- **`mock-timeout`** — Simulates timeout errors
- **`mock-unhealthy`** — Health check returns `False` (useful for testing `first-available` strategy)
- **`mock-ratelimit`** — Simulates rate limit errors
- **`mock-auth-error`** — Simulates authentication failures

See [mock.py](src/orchestrator/providers/mock.py) for all available modes and detailed documentation.

## Roadmap

See our [GitHub Issues](https://github.com/MikhailMalorod/Multi-LLM-Orchestrator/issues) for planned features and roadmap updates.

### Current Status

- ✅ Core architecture with Router and BaseProvider
- ✅ MockProvider for testing
- ✅ GigaChatProvider with OAuth2 authentication
- ✅ Three routing strategies (round-robin, random, first-available)
- ✅ Automatic fallback mechanism
- ✅ Example demonstrations

### Supported Providers

- ✅ **MockProvider** — For testing and development
- ✅ **GigaChatProvider** — Full integration with GigaChat (Sber) API
  - OAuth2 authentication with automatic token refresh
  - Support for all generation parameters
  - Comprehensive error handling
- ✅ **YandexGPTProvider** — Full integration with YandexGPT (Yandex Cloud) API
  - IAM token authentication (user-managed, 12-hour validity)
  - Support for temperature and maxTokens parameters
  - Support for yandexgpt/latest and yandexgpt-lite/latest models
  - Comprehensive error handling
- ✅ **OllamaProvider** — Local models (Llama 3, Mistral, Phi) via Ollama API

### Planned Providers

- [ ] Additional open-source providers (TBD)

## LangChain Integration

> **Note:** Requires optional dependency. Install with:
> ```bash
> pip install multi-llm-orchestrator[langchain]
> ```

Use Multi-LLM Orchestrator providers with LangChain chains, prompts, and other LangChain components:

```python
from langchain_core.prompts import ChatPromptTemplate
from orchestrator.langchain import MultiLLMOrchestrator
from orchestrator import Router
from orchestrator.providers import GigaChatProvider, ProviderConfig

# Create router with providers
router = Router(strategy="round-robin")
config = ProviderConfig(
    name="gigachat",
    api_key="your_api_key",
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

The `MultiLLMOrchestrator` class implements LangChain's `BaseLLM` interface, supporting both synchronous and asynchronous calls. All routing strategies and fallback mechanisms work seamlessly with LangChain.

## Streaming Support

Multi-LLM Orchestrator now supports streaming responses, allowing you to receive text chunks incrementally as they are generated. This is especially useful for real-time applications and improved user experience.

### Basic Streaming with Router

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import ProviderConfig, MockProvider

async def main():
    router = Router(strategy="round-robin")
    config = ProviderConfig(name="mock", model="mock-normal")
    router.add_provider(MockProvider(config))
    
    # Stream response chunk by chunk
    async for chunk in router.route_stream("What is Python?"):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

### Streaming with LangChain

```python
from orchestrator.langchain import MultiLLMOrchestrator
from orchestrator import Router
from orchestrator.providers import MockProvider, ProviderConfig

router = Router(strategy="round-robin")
router.add_provider(MockProvider(ProviderConfig(name="mock", model="mock-normal")))

llm = MultiLLMOrchestrator(router=router)

# Async streaming
async for chunk in llm._astream("What is Python?"):
    print(chunk, end="", flush=True)

# Sync streaming
for chunk in llm._stream("What is Python?"):
    print(chunk, end="", flush=True)
```

### Streaming Features

- **Incremental responses**: Receive text chunks as they are generated
- **Fallback support**: Automatic provider fallback works before the first chunk is yielded
- **Provider support**: Currently supported in MockProvider and GigaChatProvider
- **LangChain integration**: Full support for both sync and async streaming in LangChain

### Streaming Examples

See [streaming_demo.py](examples/streaming_demo.py) and [langchain_streaming_demo.py](examples/langchain_streaming_demo.py) for complete examples.

## Documentation

- **[Architecture Overview](docs/architecture.md)** — System design and components
- **[Contributing Guide](CONTRIBUTING.md)** — How to contribute to the project
- **[Provider Documentation](docs/providers/)** — Detailed provider guides
  - [GigaChat Provider](docs/providers/gigachat.md)
  - [YandexGPT Provider](docs/providers/yandexgpt.md)
  - [Creating Custom Provider](docs/providers/custom_provider.md)
- **[routing_demo.py](examples/routing_demo.py)** — Interactive demonstration of routing strategies and fallback mechanisms

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
