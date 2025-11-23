"""YandexGPT Provider Demo.

This script demonstrates how to use YandexGPTProvider with the Router.
It shows basic usage, custom parameters, and error handling.

Requirements:
    - YANDEXGPT_API_KEY: IAM token from Yandex Cloud
    - YANDEXGPT_FOLDER_ID: Yandex Cloud folder ID

Example:
    ```bash
    export YANDEXGPT_API_KEY="your_iam_token"
    export YANDEXGPT_FOLDER_ID="your_folder_id"
    python examples/yandexgpt_demo.py
    ```
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator import Router
from orchestrator.providers import GenerationParams, ProviderConfig, YandexGPTProvider


async def main() -> None:
    """Demonstrate YandexGPTProvider usage."""
    print("=" * 60)
    print("YandexGPT Provider Demo")
    print("=" * 60)
    print()

    # Get credentials from environment
    api_key = os.getenv("YANDEXGPT_API_KEY")
    folder_id = os.getenv("YANDEXGPT_FOLDER_ID")

    if not api_key or not folder_id:
        print("❌ Error: YANDEXGPT_API_KEY and YANDEXGPT_FOLDER_ID must be set")
        print()
        print("Set them in your environment or .env file:")
        print("  export YANDEXGPT_API_KEY='your_iam_token'")
        print("  export YANDEXGPT_FOLDER_ID='your_folder_id'")
        sys.exit(1)

    # Create YandexGPT provider
    print("📦 Creating YandexGPTProvider...")
    config = ProviderConfig(
        name="yandexgpt",
        api_key=api_key,
        folder_id=folder_id,
        model="yandexgpt/latest",  # or "yandexgpt-lite/latest"
        timeout=60,
        max_retries=3,
    )
    provider = YandexGPTProvider(config)
    print("✅ Provider created successfully")
    print()

    # Health check
    print("🏥 Performing health check...")
    is_healthy = await provider.health_check()
    if is_healthy:
        print("✅ Provider is healthy")
    else:
        print("❌ Provider is unhealthy - check your credentials")
        sys.exit(1)
    print()

    # Example 1: Simple generation
    print("=" * 60)
    print("Example 1: Simple Generation")
    print("=" * 60)
    prompt = "What is Python programming language? Answer in one sentence."
    print(f"Prompt: {prompt}")
    print()

    try:
        response = await provider.generate(prompt)
        print(f"Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Example 2: Generation with custom parameters
    print("=" * 60)
    print("Example 2: Generation with Custom Parameters")
    print("=" * 60)
    prompt = "Write a short haiku about programming."
    print(f"Prompt: {prompt}")
    print()

    params = GenerationParams(
        temperature=0.9,  # More creative
        max_tokens=100,   # Shorter response
    )
    print(f"Parameters: temperature={params.temperature}, max_tokens={params.max_tokens}")
    print()

    try:
        response = await provider.generate(prompt, params=params)
        print(f"Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Example 3: Using with Router
    print("=" * 60)
    print("Example 3: Using with Router")
    print("=" * 60)
    router = Router(strategy="round-robin")
    router.add_provider(provider)
    print("✅ Router configured with YandexGPTProvider")
    print()

    prompt = "Explain async/await in Python in one sentence."
    print(f"Prompt: {prompt}")
    print()

    try:
        response = await router.route(prompt)
        print(f"Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Example 4: Using yandexgpt-lite model
    print("=" * 60)
    print("Example 4: Using yandexgpt-lite Model")
    print("=" * 60)
    lite_config = ProviderConfig(
        name="yandexgpt-lite",
        api_key=api_key,
        folder_id=folder_id,
        model="yandexgpt-lite/latest",
    )
    lite_provider = YandexGPTProvider(lite_config)
    print("✅ Lite provider created")
    print()

    prompt = "What is machine learning?"
    print(f"Prompt: {prompt}")
    print()

    try:
        response = await lite_provider.generate(prompt)
        print(f"Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    print("=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

