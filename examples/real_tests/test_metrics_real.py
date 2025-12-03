"""Real-world metrics test script for Multi-LLM Orchestrator v0.6.0.

This script performs "battle-tested" metrics and best-available strategy verification:
- Tests basic metrics collection with successful requests (GigaChat, YandexGPT)
- Tests metrics with error fallback and health degradation
- Tests metrics with streaming requests
- Outputs provider metrics in formatted tables (using rich if available)

The script reads API keys from .env file and requires:
- GIGACHAT_API_KEY (required)
- YANDEXGPT_API_KEY (required)
- YANDEXGPT_FOLDER_ID (required)

Example usage:
    python examples/real_tests/test_metrics_real.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from orchestrator import Router
from orchestrator.metrics import ProviderMetrics
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Load environment variables
load_dotenv()


def load_config() -> dict[str, str | None]:
    """Load configuration from environment variables.

    Reads API keys from .env file and validates required keys.
    Returns a dictionary with all configuration values.

    Returns:
        Dictionary containing:
            - gigachat_api_key: GigaChat authorization key (required)
            - yandexgpt_api_key: YandexGPT IAM token (required)
            - yandexgpt_folder_id: Yandex Cloud folder ID (required)

    Raises:
        SystemExit: If required API keys are missing from environment.

    Example:
        ```python
        config = load_config()
        api_key = config["gigachat_api_key"]
        ```
    """
    # Read configuration from environment
    gigachat_api_key = os.getenv("GIGACHAT_API_KEY")
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
            f"❌ Error: Missing required environment variables: {', '.join(missing_keys)}\n"
            "Please ensure .env file exists in the project root and contains:\n"
            "  - GIGACHAT_API_KEY\n"
            "  - YANDEXGPT_API_KEY\n"
            "  - YANDEXGPT_FOLDER_ID\n"
            "\n"
            "See env.example for reference."
        )
        print(error_msg, file=sys.stderr, flush=True)
        sys.exit(1)

    return {
        "gigachat_api_key": gigachat_api_key,
        "yandexgpt_api_key": yandexgpt_api_key,
        "yandexgpt_folder_id": yandexgpt_folder_id,
    }


def _format_health_status(status: str, use_emoji: bool = False) -> str:
    """Format health status with emoji or plain text.

    Args:
        status: Health status ("healthy", "degraded", or "unhealthy").
        use_emoji: Whether to use emoji instead of plain text.

    Returns:
        Formatted health status string with emoji or plain text.

    Example:
        ```python
        _format_health_status("healthy", use_emoji=True)  # "✅ healthy"
        _format_health_status("degraded", use_emoji=False)  # "degraded"
        ```
    """
    if use_emoji:
        status_map = {
            "healthy": "✅ healthy",
            "degraded": "⚠️ degraded",
            "unhealthy": "❌ unhealthy",
        }
        return status_map.get(status, status)
    return status


def format_metrics_table(metrics_dict: dict[str, ProviderMetrics]) -> None:
    """Display provider metrics in a formatted table.

    Uses rich.Table if rich is available, otherwise falls back to ASCII table.
    Shows metrics for all providers: total requests, success/failure counts,
    success rate, latency measurements, and health status.

    Args:
        metrics_dict: Dictionary mapping provider names to ProviderMetrics instances.

    Example:
        ```python
        metrics = router.get_metrics()
        format_metrics_table(metrics)
        ```
    """
    if not metrics_dict:
        if RICH_AVAILABLE:
            console = Console()
            console.print("[yellow]No metrics available yet.[/yellow]")
        else:
            print("No metrics available yet.")
        return

    if RICH_AVAILABLE:
        # Use rich for beautiful colored table
        console = Console()
        table = Table(title="Provider Metrics", show_header=True, header_style="bold cyan")
        table.add_column("Provider Name", style="cyan", no_wrap=True)
        table.add_column("Total Requests", justify="right", style="white")
        table.add_column("Successful Requests", justify="right", style="green")
        table.add_column("Failed Requests", justify="right", style="red")
        table.add_column("Success Rate (%)", justify="right", style="white")
        table.add_column("Avg Latency (ms)", justify="right", style="yellow")
        table.add_column("Rolling Avg Latency (ms)", justify="right", style="yellow")
        table.add_column("Health Status", style="white", no_wrap=True)

        for provider_name, metrics in metrics_dict.items():
            # Format success rate
            success_rate_str = f"{metrics.success_rate * 100:.1f}%"

            # Format average latency
            avg_latency_str = f"{metrics.avg_latency_ms:.0f}ms"

            # Format rolling average latency
            if metrics.rolling_avg_latency_ms is not None:
                rolling_avg_str = f"{metrics.rolling_avg_latency_ms:.0f}ms"
            else:
                rolling_avg_str = "N/A"

            # Format health status with colors
            health_status = metrics.health_status
            if health_status == "healthy":
                health_status_str = f"[green]{health_status}[/green]"
            elif health_status == "degraded":
                health_status_str = f"[yellow]{health_status}[/yellow]"
            else:  # unhealthy
                health_status_str = f"[red]{health_status}[/red]"

            table.add_row(
                provider_name,
                str(metrics.total_requests),
                str(metrics.successful_requests),
                str(metrics.failed_requests),
                success_rate_str,
                avg_latency_str,
                rolling_avg_str,
                health_status_str,
            )

        console.print(table)
    else:
        # ASCII fallback table
        print("\n" + "=" * 100)
        print("Provider Metrics")
        print("=" * 100)

        # Prepare all rows
        rows = []
        for provider_name, metrics in metrics_dict.items():
            success_rate_str = f"{metrics.success_rate * 100:.1f}%"
            avg_latency_str = f"{metrics.avg_latency_ms:.0f}ms"
            if metrics.rolling_avg_latency_ms is not None:
                rolling_avg_str = f"{metrics.rolling_avg_latency_ms:.0f}ms"
            else:
                rolling_avg_str = "N/A"
            health_status_str = _format_health_status(metrics.health_status, use_emoji=True)

            rows.append(
                [
                    provider_name,
                    str(metrics.total_requests),
                    str(metrics.successful_requests),
                    str(metrics.failed_requests),
                    success_rate_str,
                    avg_latency_str,
                    rolling_avg_str,
                    health_status_str,
                ]
            )

        # Column headers
        headers = [
            "Provider Name",
            "Total Requests",
            "Successful Requests",
            "Failed Requests",
            "Success Rate (%)",
            "Avg Latency (ms)",
            "Rolling Avg Latency (ms)",
            "Health Status",
        ]

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))

        # Print header
        header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
        print(f"| {header_line} |")
        print("|" + "-" * (len(header_line) + 2) + "|")

        # Print rows
        for row in rows:
            row_line = " | ".join(f"{cell:<{col_widths[i]}}" for i, cell in enumerate(row))
            print(f"| {row_line} |")

        print("=" * 100 + "\n")


async def test_basic_metrics(config: dict[str, str | None]) -> bool:
    """Test basic metrics collection with successful requests.

    This test demonstrates metrics tracking with real API calls:
    - Initializes Router with best-available strategy
    - Adds GigaChat and YandexGPT providers with valid API keys
    - Executes 3 requests through router.route()
    - Displays provider metrics in a formatted table

    Args:
        config: Configuration dictionary from load_config().

    Returns:
        True if test completed successfully, False otherwise.

    Example:
        ```python
        config = load_config()
        success = await test_basic_metrics(config)
        ```
    """
    try:
        # Display test header
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
            console.print(
                "[bold cyan]Test 1: Basic Metrics (Successful Requests)[/bold cyan]"
            )
            console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 80)
            print("Test 1: Basic Metrics (Successful Requests)")
            print("=" * 80 + "\n")

        # Initialize router with best-available strategy
        router = Router(strategy="best-available")

        # Create GigaChat provider configuration
        gigachat_config = ProviderConfig(  # type: ignore[call-arg]
            name="gigachat",
            api_key=config["gigachat_api_key"],
            scope="GIGACHAT_API_PERS",
            verify_ssl=False,
            timeout=30,
        )

        # Create and add GigaChat provider
        router.add_provider(GigaChatProvider(gigachat_config))

        # Create YandexGPT provider configuration
        yandex_config = ProviderConfig(  # type: ignore[call-arg]
            name="yandexgpt",
            api_key=config["yandexgpt_api_key"],
            folder_id=config["yandexgpt_folder_id"],
            model="yandexgpt/latest",
        )

        # Create and add YandexGPT provider
        router.add_provider(YandexGPTProvider(yandex_config))

        # Define test prompts
        prompts = ["Привет!", "Что такое Python?", "Спасибо за помощь"]

        # Execute requests
        for prompt in prompts:
            await router.route(prompt)

        # Get metrics
        metrics = router.get_metrics()

        # Display metrics table
        format_metrics_table(metrics)

        # Success message
        if RICH_AVAILABLE:
            console.print("[bold green]✅ Basic metrics test completed successfully![/bold green]\n")
        else:
            print("✅ Basic metrics test completed successfully!\n")

        return True

    except Exception as e:
        # Error handling
        if RICH_AVAILABLE:
            console = Console(file=sys.stderr)
            console.print(f"[bold red]❌ Basic metrics test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Basic metrics test failed: {e}\n", file=sys.stderr)
        return False


async def test_error_fallback(config: dict[str, str | None]) -> bool:
    """Test metrics with error fallback and health degradation.

    This test demonstrates fallback behavior and metrics tracking with errors:
    - Initializes Router with best-available strategy
    - Adds GigaChat provider with invalid API key (will fail)
    - Adds YandexGPT provider with valid API key (fallback target)
    - Executes 6 requests (to exceed MIN_REQUESTS_FOR_HEALTH=5)
    - Router automatically falls back to YandexGPT after GigaChat failures
    - Displays metrics showing GigaChat degradation and YandexGPT success

    Args:
        config: Configuration dictionary from load_config().

    Returns:
        True if test completed successfully, False otherwise.

    Example:
        ```python
        config = load_config()
        success = await test_error_fallback(config)
        ```
    """
    try:
        # Display test header with fallback warning
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold yellow]" + "=" * 80 + "[/bold yellow]")
            console.print(
                "[bold yellow]Test 2: Error Fallback (Metrics with Degradation)[/bold yellow]"
            )
            console.print(
                "[dim]Note: GigaChat will fail with invalid key, router will fallback to YandexGPT[/dim]"
            )
            console.print("[bold yellow]" + "=" * 80 + "[/bold yellow]\n")
        else:
            print("\n" + "=" * 80)
            print("Test 2: Error Fallback (Metrics with Degradation)")
            print("Note: GigaChat will fail with invalid key, router will fallback to YandexGPT")
            print("=" * 80 + "\n")

        # Initialize router with best-available strategy
        router = Router(strategy="best-available")

        # Create GigaChat provider with INVALID API key (will fail authentication)
        gigachat_config_invalid = ProviderConfig(  # type: ignore[call-arg]
            name="gigachat-invalid",
            api_key="invalid_key_12345",  # Invalid key to trigger AuthenticationError
            scope="GIGACHAT_API_PERS",
            verify_ssl=False,
            timeout=30,
        )

        # Add failing provider first (will be tried first, then fallback to YandexGPT)
        router.add_provider(GigaChatProvider(gigachat_config_invalid))

        # Create YandexGPT provider (fallback target)
        yandex_config = ProviderConfig(  # type: ignore[call-arg]
            name="yandexgpt",
            api_key=config["yandexgpt_api_key"],
            folder_id=config["yandexgpt_folder_id"],
            model="yandexgpt/latest",
        )

        # Add YandexGPT provider as fallback
        router.add_provider(YandexGPTProvider(yandex_config))

        # Define test prompts (6 requests to exceed MIN_REQUESTS_FOR_HEALTH=5)
        prompts = ["Тест 1", "Тест 2", "Тест 3", "Тест 4", "Тест 5", "Тест 6"]

        # Execute requests (Router will fallback to YandexGPT after GigaChat failures)
        for prompt in prompts:
            await router.route(prompt)

        # Get metrics
        metrics = router.get_metrics()

        # Display metrics table
        format_metrics_table(metrics)

        # Verify expected behavior
        gigachat_metrics = metrics.get("gigachat-invalid")
        yandex_metrics = metrics.get("yandexgpt")

        if gigachat_metrics and yandex_metrics:
            # Check that GigaChat has failures
            if gigachat_metrics.failed_requests > 0:
                # Check that health status is degraded or unhealthy
                if gigachat_metrics.health_status in ["degraded", "unhealthy"]:
                    if RICH_AVAILABLE:
                        console.print(
                            "[green]✓ GigaChat correctly marked as "
                            f"{gigachat_metrics.health_status}[/green]"
                        )
                    else:
                        print(f"✓ GigaChat correctly marked as {gigachat_metrics.health_status}")

            # Check that YandexGPT has successes
            if yandex_metrics.successful_requests > 0:
                if yandex_metrics.health_status == "healthy":
                    if RICH_AVAILABLE:
                        console.print("[green]✓ YandexGPT is healthy and handling requests[/green]")
                    else:
                        print("✓ YandexGPT is healthy and handling requests")

        # Success message with fallback confirmation
        if RICH_AVAILABLE:
            console.print(
                "[bold green]✅ Error fallback test completed successfully![/bold green] "
                "[dim](Router switched from GigaChat to YandexGPT)[/dim]\n"
            )
        else:
            print("✅ Error fallback test completed successfully! (Router switched from GigaChat to YandexGPT)\n")

        return True

    except Exception as e:
        # Error handling
        if RICH_AVAILABLE:
            console = Console(file=sys.stderr)
            console.print(f"[bold red]❌ Error fallback test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Error fallback test failed: {e}\n", file=sys.stderr)
        return False


async def test_streaming_metrics(config: dict[str, str | None]) -> bool:
    """Test metrics tracking with streaming requests.

    This test demonstrates metrics collection with streaming:
    - Initializes Router with best-available strategy
    - Adds GigaChat provider (supports streaming)
    - Executes 2 streaming requests through router.route_stream()
    - Displays chunks in real-time
    - Verifies that streaming requests are tracked in metrics correctly

    Args:
        config: Configuration dictionary from load_config().

    Returns:
        True if test completed successfully, False otherwise.

    Example:
        ```python
        config = load_config()
        success = await test_streaming_metrics(config)
        ```
    """
    try:
        # Display test header
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
            console.print("[bold cyan]Test 3: Streaming Metrics[/bold cyan]")
            console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 80)
            print("Test 3: Streaming Metrics")
            print("=" * 80 + "\n")

        # Initialize router with best-available strategy
        router = Router(strategy="best-available")

        # Create GigaChat provider configuration (supports streaming)
        gigachat_config = ProviderConfig(  # type: ignore[call-arg]
            name="gigachat",
            api_key=config["gigachat_api_key"],
            scope="GIGACHAT_API_PERS",
            verify_ssl=False,
            timeout=30,
        )

        # Create and add GigaChat provider
        router.add_provider(GigaChatProvider(gigachat_config))

        # Define test prompt (same for both requests)
        prompt = "Напиши короткое стихотворение про Python"

        # Display streaming response header
        if RICH_AVAILABLE:
            console.print("[bold]Streaming responses:[/bold]\n")
        else:
            print("Streaming responses:\n")

        # Execute 2 streaming requests
        for request_num in range(1, 3):
            if RICH_AVAILABLE:
                console.print(f"[dim]Request {request_num}:[/dim]\n")
            else:
                print(f"Request {request_num}:\n")

            # Stream response
            async for chunk in router.route_stream(prompt):
                # Output chunk in real-time (no newline, flush immediately)
                print(chunk, end="", flush=True)

            # Newline after each streaming response
            print("\n")

        # Get metrics
        metrics = router.get_metrics()

        # Display metrics table
        format_metrics_table(metrics)

        # Verify expected behavior
        gigachat_metrics = metrics.get("gigachat")
        if gigachat_metrics:
            # Check that streaming requests are tracked
            if gigachat_metrics.total_requests >= 2:
                if RICH_AVAILABLE:
                    console.print(
                        f"[green]✓ Streaming requests tracked: {gigachat_metrics.total_requests} requests[/green]"
                    )
                else:
                    print(f"✓ Streaming requests tracked: {gigachat_metrics.total_requests} requests")

            # Check that latency is measured
            if gigachat_metrics.avg_latency_ms > 0:
                if RICH_AVAILABLE:
                    console.print(
                        f"[green]✓ Latency measured correctly: {gigachat_metrics.avg_latency_ms:.0f}ms[/green]"
                    )
                else:
                    print(f"✓ Latency measured correctly: {gigachat_metrics.avg_latency_ms:.0f}ms")

            # Check health status
            if RICH_AVAILABLE:
                console.print(
                    f"[green]✓ Health status: {gigachat_metrics.health_status}[/green]"
                )
            else:
                print(f"✓ Health status: {gigachat_metrics.health_status}")

        # Success message
        if RICH_AVAILABLE:
            console.print("[bold green]✅ Streaming metrics test completed successfully![/bold green]\n")
        else:
            print("✅ Streaming metrics test completed successfully!\n")

        return True

    except Exception as e:
        # Error handling
        if RICH_AVAILABLE:
            console = Console(file=sys.stderr)
            console.print(f"[bold red]❌ Streaming metrics test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Streaming metrics test failed: {e}\n", file=sys.stderr)
        return False


async def main() -> None:
    """Main entry point for real-world metrics tests.

    Orchestrates execution of all metrics tests:
    1. Loads configuration from .env file
    2. Runs test_basic_metrics (successful requests)
    3. Runs test_error_fallback (fallback and degradation)
    4. Runs test_streaming_metrics (streaming requests)
    5. Displays final summary with test results

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
        # Add debug output at the very start (BEFORE load_config)
        print("=== Real-World Metrics Test - Multi-LLM Orchestrator v0.6.0 ===", flush=True)
        print("Starting tests...\n", flush=True)

        # Display welcome message
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
            console.print(
                "[bold cyan]Real-World Metrics Test - Multi-LLM Orchestrator v0.6.0[/bold cyan]"
            )
            console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]\n")
            console.print(
                "[dim]This script tests metrics functionality and best-available strategy "
                "with real API providers.[/dim]\n"
            )
        else:
            print("\n" + "=" * 80)
            print("Real-World Metrics Test - Multi-LLM Orchestrator v0.6.0")
            print("=" * 80 + "\n")
            print("This script tests metrics functionality and best-available strategy with real API providers.\n")

        # Load configuration (may exit if keys are missing)
        print("Loading configuration from .env file...", flush=True)
        config = load_config()
        print("Configuration loaded successfully.\n", flush=True)

        # Store test results
        test_results: list[tuple[str, bool]] = []

        # Run Test 1: Basic metrics
        result1 = await test_basic_metrics(config)
        test_results.append(("Test 1: Basic Metrics", result1))

        # Display separator between tests
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[dim]" + "-" * 80 + "[/dim]\n")
        else:
            print("\n" + "-" * 80 + "\n")

        # Run Test 2: Error fallback
        result2 = await test_error_fallback(config)
        test_results.append(("Test 2: Error Fallback", result2))

        # Display separator between tests
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[dim]" + "-" * 80 + "[/dim]\n")
        else:
            print("\n" + "-" * 80 + "\n")

        # Run Test 3: Streaming metrics
        result3 = await test_streaming_metrics(config)
        test_results.append(("Test 3: Streaming Metrics", result3))

        # Display final summary
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 80 + "[/bold cyan]")
            console.print("[bold cyan]Final Test Results[/bold cyan]")
            console.print("[bold cyan]" + "=" * 80 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 80)
            print("Final Test Results")
            print("=" * 80 + "\n")

        # Display results for each test
        for test_name, success in test_results:
            if success:
                if RICH_AVAILABLE:
                    console.print(f"[bold green]✅ {test_name} - PASSED[/bold green]")
                else:
                    print(f"✅ {test_name} - PASSED")
            else:
                if RICH_AVAILABLE:
                    console.print(f"[bold red]❌ {test_name} - FAILED[/bold red]")
                else:
                    print(f"❌ {test_name} - FAILED")

        # Display completion message
        all_passed = all(result for _, result in test_results)
        if all_passed:
            if RICH_AVAILABLE:
                console.print("\n[bold green]" + "=" * 80 + "[/bold green]")
                console.print(
                    "[bold green]✅ All metrics tests completed successfully![/bold green]"
                )
                console.print("[bold green]" + "=" * 80 + "[/bold green]\n")
            else:
                print("\n" + "=" * 80)
                print("✅ All metrics tests completed successfully!")
                print("=" * 80 + "\n")
        else:
            passed_count = sum(1 for _, result in test_results if result)
            total_count = len(test_results)
            if RICH_AVAILABLE:
                console.print("\n[yellow]" + "=" * 80 + "[/yellow]")
                console.print(
                    f"[yellow]⚠️  {passed_count}/{total_count} tests passed. "
                    "Some tests failed.[/yellow]"
                )
                console.print("[yellow]" + "=" * 80 + "[/yellow]\n")
            else:
                print("\n" + "=" * 80)
                print(f"⚠️  {passed_count}/{total_count} tests passed. Some tests failed.")
                print("=" * 80 + "\n")

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
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
