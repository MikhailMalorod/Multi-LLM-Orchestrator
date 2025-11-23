# Multi-LLM Orchestrator

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PyPI](https://img.shields.io/pypi/v/multi-llm-orchestrator.svg)
![Coverage](https://img.shields.io/badge/coverage-88%25-brightgreen.svg)
![Tests](https://img.shields.io/badge/tests-79%20passed-success.svg)

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
         │     Router      │ ◄── Strategy: round-robin/random/first-available
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

See [STRATEGY.md](STRATEGY.md) for the detailed roadmap and development plan.

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

### Planned Providers

- [ ] Ollama (local models)

## Documentation

- **[STRATEGY.md](STRATEGY.md)** — Project roadmap and development plan
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
