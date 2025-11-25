# Ollama Provider

OllamaProvider enables Multi-LLM Orchestrator to work with local LLM models
powered by [Ollama](https://ollama.ai). It keeps all prompts and completions on
your machine, making it ideal for privacy-sensitive workloads or offline
environments.

## Overview

- **Local inference** — Runs open-source models such as Llama 3, Mistral, Phi.
- **Zero API keys** — Communicates with `http://localhost:11434` by default.
- **Drop-in provider** — Reuses the same router/routing strategies as cloud
  providers.

## Installation

1. Install Ollama following the official guide: <https://ollama.ai>.
2. Start the Ollama daemon (`ollama serve`) if it is not already running.
3. Pull one or more models:

```bash
ollama pull llama3
ollama pull mistral
ollama pull phi
```

## Configuration

```python
from orchestrator.providers import OllamaProvider, ProviderConfig

config = ProviderConfig(
    name="ollama",
    model="llama3",                  # Required model name
    base_url="http://localhost:11434"  # Optional, defaults to localhost
)
provider = OllamaProvider(config)
```

- `model` is **required** and must match a pulled model tag.
- `base_url` is optional; set it if you expose Ollama over a different host or
  via SSH tunnel.
- `timeout`, `max_retries`, and other `ProviderConfig` fields are fully
  supported.

## Supported Parameters

`GenerationParams` are translated to Ollama's `options` block:

| GenerationParams | Ollama option |
|------------------|---------------|
| `temperature`    | `temperature` |
| `max_tokens`     | `num_predict` |
| `top_p`          | `top_p`       |

`stop` sequences are currently ignored (planned for v0.4.0).

## Example Usage

```python
import asyncio
from orchestrator import Router
from orchestrator.providers import OllamaProvider, ProviderConfig
from orchestrator.providers.base import GenerationParams

async def main():
    router = Router(strategy="first-available")

    ollama_config = ProviderConfig(
        name="ollama-local",
        model="llama3",
        base_url="http://localhost:11434",
    )
    router.add_provider(OllamaProvider(ollama_config))

    params = GenerationParams(temperature=0.2, max_tokens=128, top_p=0.9)
    response = await router.route("Explain diffusion models in two sentences.", params=params)
    print(response)

asyncio.run(main())
```

## Troubleshooting

- **Cannot connect to Ollama** — Ensure `ollama serve` is running and that the
  configured `base_url` is reachable.
- **Model not found** — Pull the model first (`ollama pull llama3`) or double
  check the `model` name in `ProviderConfig`.
- **Slow generation** — Performance depends on local CPU/GPU. Consider using a
  lighter model (e.g., `mistral`) for faster responses.

## API Reference

- Ollama REST API docs: <https://github.com/ollama/ollama/blob/main/docs/api.md>
- Provider implementation: `src/orchestrator/providers/ollama.py`

