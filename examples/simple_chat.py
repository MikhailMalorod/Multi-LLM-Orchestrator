#!/usr/bin/env python3
"""Simple chat example for Multi-LLM Orchestrator.

This example demonstrates basic usage of the orchestrator
for simple chat interactions.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestrator import LLMRouter, Config


async def main() -> None:
    """Main example function."""
    print("Multi-LLM Orchestrator - Simple Chat Example")
    print("=" * 50)
    
    # Load configuration
    try:
        config = Config.from_env()
        print("✓ Configuration loaded")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return
        
    # Initialize router
    try:
        router = LLMRouter(config.to_dict())
        print("✓ Router initialized")
    except Exception as e:
        print(f"✗ Failed to initialize router: {e}")
        return
        
    # Example chat interaction
    message = "Hello! Can you tell me about yourself?"
    print(f"\nUser: {message}")
    
    try:
        # This will raise NotImplementedError for now
        response = await router.chat(message)
        print(f"Assistant: {response}")
    except NotImplementedError:
        print("Assistant: [Implementation coming soon - this is a placeholder]")
    except Exception as e:
        print(f"✗ Error during chat: {e}")
        

if __name__ == "__main__":
    # Run the example
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
