"""Real-world streaming test script for Multi-LLM Orchestrator v0.5.0.

This script performs "battle-tested" streaming functionality verification:
- Tests real GigaChat streaming with live API calls
- Measures Time to First Token (TTFT) and total generation time
- Demonstrates fallback behavior (GigaChat → YandexGPT) on authentication errors
- Outputs metrics in a formatted table (using rich if available)

The script reads API keys from .env file and requires:
- GIGACHAT_API_KEY (required)
- GIGACHAT_SCOPE (optional, defaults to GIGACHAT_API_PERS)
- YANDEXGPT_API_KEY (required for fallback test)
- YANDEXGPT_FOLDER_ID (required for fallback test)

Example usage:
    python examples/real_tests/test_streaming_real.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from orchestrator import Router
from orchestrator.providers import (
    GigaChatProvider,
    ProviderConfig,
    YandexGPTProvider,
)

# Try to import rich for beautiful output (optional dependency)
try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Load environment variables
load_dotenv()


def load_config() -> dict[str, str | None]:
    """Load configuration from environment variables.

    Reads API keys and settings from .env file and validates required keys.
    Returns a dictionary with all configuration values.

    Returns:
        Dictionary containing:
            - gigachat_api_key: GigaChat authorization key (required)
            - gigachat_scope: OAuth2 scope (defaults to GIGACHAT_API_PERS)
            - yandexgpt_api_key: YandexGPT IAM token (required for fallback test)
            - yandexgpt_folder_id: Yandex Cloud folder ID (required for fallback test)

    Raises:
        SystemExit: If required API keys are missing from environment.

    Example:
        ```python
        config = load_config()
        api_key = config["gigachat_api_key"]
        ```
    """
    # Read GigaChat configuration
    gigachat_api_key = os.getenv("GIGACHAT_API_KEY")
    gigachat_scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

    # Read YandexGPT configuration
    yandexgpt_api_key = os.getenv("YANDEXGPT_API_KEY")
    yandexgpt_folder_id = os.getenv("YANDEXGPT_FOLDER_ID")

    # Validate required keys
    missing_keys = []
    if not gigachat_api_key:
        missing_keys.append("GIGACHAT_API_KEY")
    if not yandexgpt_api_key:
        missing_keys.append("YANDEXGPT_API_KEY")
    if not yandexgpt_folder_id:
        missing_keys.append("YANDEXGPT_FOLDER_ID")

    if missing_keys:
        error_msg = (
            f"❌ Missing required environment variables: {', '.join(missing_keys)}\n"
            "Please create a .env file with these variables.\n"
            "See env.example for reference."
        )
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    return {
        "gigachat_api_key": gigachat_api_key,
        "gigachat_scope": gigachat_scope,
        "yandexgpt_api_key": yandexgpt_api_key,
        "yandexgpt_folder_id": yandexgpt_folder_id,
    }


def format_time(seconds: float) -> str:
    """Format time duration in a human-readable format.

    Formats time in milliseconds for values < 1 second,
    and in seconds for values >= 1 second.

    Args:
        seconds: Time duration in seconds.

    Returns:
        Formatted time string (e.g., "450ms", "2.3s").

    Example:
        ```python
        format_time(0.45)  # "450ms"
        format_time(2.3)   # "2.3s"
        ```
    """
    if seconds < 1.0:
        return f"{int(seconds * 1000)}ms"
    return f"{seconds:.1f}s"


def format_metrics_table(metrics: dict[str, str]) -> None:
    """Display metrics in a formatted table.

    Uses rich.Table if rich is available, otherwise falls back to ASCII table.

    Args:
        metrics: Dictionary with metric names as keys and formatted values as strings.
                Expected keys: "TTFT", "Total Time", "Tokens Generated", "Speed".

    Example:
        ```python
        metrics = {
            "TTFT": "450ms",
            "Total Time": "2.3s",
            "Tokens Generated": "45",
            "Speed": "19 tok/s"
        }
        format_metrics_table(metrics)
        ```
    """
    if RICH_AVAILABLE:
        # Use rich for beautiful colored table
        console = Console()
        table = Table(title="Streaming Metrics", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")

        for metric_name, value in metrics.items():
            table.add_row(metric_name, value)

        console.print(table)
    else:
        # ASCII fallback table
        print("\n" + "=" * 40)
        print("Streaming Metrics")
        print("=" * 40)
        # Calculate column widths
        max_name_len = max(len(name) for name in metrics.keys())
        max_value_len = max(len(str(value)) for value in metrics.values())

        # Print header
        print(f"| {'Metric':<{max_name_len}} | {'Value':<{max_value_len}} |")
        print(f"|{'-' * (max_name_len + 2)}|{'-' * (max_value_len + 2)}|")

        # Print rows
        for metric_name, value in metrics.items():
            print(f"| {metric_name:<{max_name_len}} | {str(value):<{max_value_len}} |")

        print("=" * 40 + "\n")


async def test_successful_streaming(config: dict[str, str | None]) -> None:
    """Test successful streaming through GigaChat provider.

    This test demonstrates real-time streaming with live API calls:
    - Initializes Router with GigaChatProvider
    - Sends a prompt and streams the response token by token
    - Measures Time to First Token (TTFT) and total generation time
    - Displays streaming text in real-time and outputs metrics table

    Args:
        config: Configuration dictionary from load_config().

    Raises:
        Exception: If streaming fails or provider is unavailable.

    Example:
        ```python
        config = load_config()
        await test_successful_streaming(config)
        ```
    """
    # Initialize router with round-robin strategy
    router = Router(strategy="round-robin")

    # Create GigaChat provider configuration
    # Note: verify_ssl=False is required for GigaChat due to self-signed certificates
    # from Russian CA that often cause issues on local machines
    gigachat_config = ProviderConfig(  # type: ignore[call-arg]
        name="gigachat",
        api_key=config["gigachat_api_key"],
        scope=config["gigachat_scope"],
        model="GigaChat",
        timeout=30,  # int, not float
        verify_ssl=False,  # Disable SSL verification for GigaChat with self-signed certificates
    )

    # Create and add provider to router
    provider = GigaChatProvider(gigachat_config)
    router.add_provider(provider)

    # Define test prompt
    prompt = "Напиши короткое стихотворение про Python"

    # Display test header
    if RICH_AVAILABLE:
        console = Console()
        console.print("\n[bold cyan]Test 1: Successful Streaming (GigaChat)[/bold cyan]")
        console.print(f"[dim]Prompt: {prompt}[/dim]\n")
    else:
        print("\n" + "=" * 60)
        print("Test 1: Successful Streaming (GigaChat)")
        print(f"Prompt: {prompt}")
        print("=" * 60 + "\n")

    # Record start time for TTFT and total time measurement
    start_time = time.perf_counter()
    first_chunk_time: float | None = None
    token_count = 0

    # Display streaming response header
    if RICH_AVAILABLE:
        console.print("[bold]Streaming response:[/bold]\n")
    else:
        print("Streaming response:\n")

    # Stream response and measure metrics
    try:
        async for chunk in router.route_stream(prompt):
            # Record time of first chunk (TTFT measurement)
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter()

            # Output chunk in real-time (no newline, flush immediately)
            print(chunk, end="", flush=True)

            # Approximate token count (character-based estimation)
            # Note: This is an approximation, not exact token count
            token_count += len(chunk)

        # Record end time
        end_time = time.perf_counter()

        # Calculate metrics
        ttft_ms = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0.0
        total_time_sec = end_time - start_time
        speed_tokens_per_sec = token_count / total_time_sec if total_time_sec > 0 else 0.0

        # Format metrics
        metrics = {
            "TTFT": format_time(ttft_ms / 1000),  # Convert back to seconds for format_time
            "Total Time": format_time(total_time_sec),
            "Tokens Generated": str(token_count),
            "Speed": f"{speed_tokens_per_sec:.1f} tok/s",
        }

        # Display metrics table
        print("\n")  # Newline after streaming output
        format_metrics_table(metrics)

        # Success message
        if RICH_AVAILABLE:
            console.print("[bold green]✅ Streaming test completed successfully![/bold green]\n")
        else:
            print("✅ Streaming test completed successfully!\n")

    except Exception as e:
        # Error handling
        if RICH_AVAILABLE:
            console = Console(file=sys.stderr)
            console.print(f"[bold red]❌ Streaming test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Streaming test failed: {e}\n", file=sys.stderr)
        raise


async def test_fallback_streaming(config: dict[str, str | None]) -> None:
    """Test fallback behavior when primary provider fails.

    This test demonstrates automatic fallback from GigaChat to YandexGPT:
    - Initializes Router with GigaChatProvider (with invalid API key) and YandexGPTProvider
    - GigaChat fails with AuthenticationError (invalid key)
    - Router automatically falls back to YandexGPT before first chunk is yielded
    - YandexGPT generates response (non-streaming, as it doesn't support streaming yet)
    - Measures metrics and displays results

    Note: Fallback only works BEFORE the first chunk is yielded. Once streaming
    starts, errors will raise immediately without trying other providers.

    Args:
        config: Configuration dictionary from load_config().

    Raises:
        Exception: If fallback fails or all providers are unavailable.

    Example:
        ```python
        config = load_config()
        await test_fallback_streaming(config)
        ```
    """
    # Initialize router with round-robin strategy
    router = Router(strategy="round-robin")

    # Create GigaChat provider with INVALID API key (will fail authentication)
    # This simulates a real-world scenario where primary provider is unavailable
    gigachat_config_fail = ProviderConfig(  # type: ignore[call-arg]
        name="gigachat-fail",
        api_key="invalid_key_12345",  # Invalid key to trigger AuthenticationError
        scope=config["gigachat_scope"],
        model="GigaChat",
        timeout=30,  # int, not float
        verify_ssl=False,  # Disable SSL verification for GigaChat
    )

    # Add failing provider first (will be tried first, then fallback to YandexGPT)
    router.add_provider(GigaChatProvider(gigachat_config_fail))

    # Create YandexGPT provider (fallback target)
    # Note: YandexGPTProvider doesn't support streaming yet, so it will return
    # the complete response as a single chunk (via BaseProvider default implementation)
    yandex_config = ProviderConfig(  # type: ignore[call-arg]
        name="yandexgpt",
        api_key=config["yandexgpt_api_key"],
        folder_id=config["yandexgpt_folder_id"],
        model="yandexgpt/latest",
    )

    # Add YandexGPT provider as fallback
    router.add_provider(YandexGPTProvider(yandex_config))

    # Define test prompt
    prompt = "Напиши короткое стихотворение про Python"

    # Display test header with fallback warning
    if RICH_AVAILABLE:
        console = Console()
        console.print("\n[bold yellow]Test 2: Fallback Streaming (GigaChat → YandexGPT)[/bold yellow]")
        console.print("[dim]Note: GigaChat will fail with invalid key, router will fallback to YandexGPT[/dim]")
        console.print(f"[dim]Prompt: {prompt}[/dim]\n")
    else:
        print("\n" + "=" * 60)
        print("Test 2: Fallback Streaming (GigaChat → YandexGPT)")
        print("Note: GigaChat will fail with invalid key, router will fallback to YandexGPT")
        print(f"Prompt: {prompt}")
        print("=" * 60 + "\n")

    # Record start time for TTFT and total time measurement
    start_time = time.perf_counter()
    first_chunk_time: float | None = None
    token_count = 0

    # Display streaming response header
    if RICH_AVAILABLE:
        console.print("[bold]Streaming response (via fallback):[/bold]\n")
    else:
        print("Streaming response (via fallback):\n")

    # Stream response and measure metrics
    # Router will try GigaChat first, get AuthenticationError, then fallback to YandexGPT
    try:
        async for chunk in router.route_stream(prompt):
            # Record time of first chunk (TTFT measurement)
            # This includes fallback time (GigaChat failure + YandexGPT connection)
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter()

            # Output chunk in real-time
            print(chunk, end="", flush=True)

            # Approximate token count
            token_count += len(chunk)

        # Record end time
        end_time = time.perf_counter()

        # Calculate metrics
        ttft_ms = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0.0
        total_time_sec = end_time - start_time
        speed_tokens_per_sec = token_count / total_time_sec if total_time_sec > 0 else 0.0

        # Format metrics
        metrics = {
            "TTFT": format_time(ttft_ms / 1000),  # Convert back to seconds for format_time
            "Total Time": format_time(total_time_sec),
            "Tokens Generated": str(token_count),
            "Speed": f"{speed_tokens_per_sec:.1f} tok/s",
        }

        # Display metrics table
        print("\n")  # Newline after streaming output
        format_metrics_table(metrics)

        # Success message with fallback confirmation
        if RICH_AVAILABLE:
            console.print(
                "[bold green]✅ Fallback test completed successfully![/bold green] "
                "[dim](Router switched from GigaChat to YandexGPT)[/dim]\n"
            )
        else:
            print("✅ Fallback test completed successfully! (Router switched from GigaChat to YandexGPT)\n")

    except Exception as e:
        # Error handling
        if RICH_AVAILABLE:
            console = Console(file=sys.stderr)
            console.print(f"[bold red]❌ Fallback test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Fallback test failed: {e}\n", file=sys.stderr)
        raise


async def main() -> None:
    """Main entry point for real-world streaming tests.

    Orchestrates execution of all streaming tests:
    1. Loads configuration from .env file
    2. Runs successful streaming test (GigaChat)
    3. Runs fallback test (GigaChat → YandexGPT)

    Handles KeyboardInterrupt gracefully and provides clear error messages.

    Raises:
        SystemExit: On KeyboardInterrupt or configuration errors.

    Example:
        ```python
        if __name__ == "__main__":
            asyncio.run(main())
        ```
    """
    try:
        # Display welcome message
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
            console.print(
                "[bold cyan]Real-World Streaming Test - Multi-LLM Orchestrator v0.5.0[/bold cyan]"
            )
            console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")
            console.print(
                "[dim]This script tests streaming functionality with real API providers.[/dim]\n"
            )
        else:
            print("\n" + "=" * 70)
            print("Real-World Streaming Test - Multi-LLM Orchestrator v0.5.0")
            print("=" * 70 + "\n")
            print("This script tests streaming functionality with real API providers.\n")

        # Load configuration
        config = load_config()

        # Run Test 1: Successful streaming
        await test_successful_streaming(config)

        # Display separator between tests
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[dim]" + "-" * 70 + "[/dim]\n")
        else:
            print("\n" + "-" * 70 + "\n")

        # Run Test 2: Fallback streaming
        await test_fallback_streaming(config)

        # Display completion message
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold green]" + "=" * 70 + "[/bold green]")
            console.print(
                "[bold green]✅ All streaming tests completed successfully![/bold green]"
            )
            console.print("[bold green]" + "=" * 70 + "[/bold green]\n")
        else:
            print("\n" + "=" * 70)
            print("✅ All streaming tests completed successfully!")
            print("=" * 70 + "\n")

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[yellow]⚠️  Test interrupted by user[/yellow]\n")
        else:
            print("\n⚠️  Test interrupted by user\n")
        sys.exit(0)
    except Exception as e:
        # Handle other errors
        if RICH_AVAILABLE:
            console = Console(file=sys.stderr)
            console.print(f"\n[bold red]❌ Test execution failed: {e}[/bold red]\n")
        else:
            print(f"\n❌ Test execution failed: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

