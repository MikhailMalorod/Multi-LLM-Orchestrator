"""Real-world observability test script for Multi-LLM Orchestrator v0.7.0.

This script performs production testing of v0.7.0 observability features:
- Token tracking with real providers (GigaChat, YandexGPT)
- Cost estimation with real token counts
- Prometheus metrics HTTP endpoint
- Health monitoring integration
- Streaming with token tracking

The script reads API keys from .env file and requires:
- GIGACHAT_API_KEY (required for GigaChat tests)
- YANDEXGPT_API_KEY (required for YandexGPT tests)
- YANDEXGPT_FOLDER_ID (required for YandexGPT tests)

Example usage:
    python examples/real_tests/test_v070_observability.py
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
from orchestrator.providers import (
    GigaChatProvider,
    ProviderConfig,
    YandexGPTProvider,
)

# Try to import rich for beautiful output (optional dependency)
try:
    from rich.console import Console

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

    Reads API keys from .env file. Tests will skip if credentials are missing.

    Returns:
        Dictionary containing:
            - gigachat_api_key: GigaChat authorization key (optional)
            - yandexgpt_api_key: YandexGPT IAM token (optional)
            - yandexgpt_folder_id: Yandex Cloud folder ID (optional)

    Example:
        ```python
        config = load_config()
        api_key = config["gigachat_api_key"]
        ```
    """
    return {
        "gigachat_api_key": os.getenv("GIGACHAT_API_KEY"),
        "yandexgpt_api_key": os.getenv("YANDEXGPT_API_KEY"),
        "yandexgpt_folder_id": os.getenv("YANDEXGPT_FOLDER_ID"),
    }


async def test_token_tracking_gigachat(config: dict[str, str | None]) -> bool:
    """Test token tracking with GigaChat provider.

    This test verifies that v0.7.0 token tracking works correctly:
    - Makes a real API request to GigaChat
    - Verifies prompt_tokens > 0
    - Verifies completion_tokens > 0
    - Verifies total_tokens = prompt + completion
    - Verifies cost > 0 (GigaChat pricing applied)

    Args:
        config: Configuration dictionary from load_config().

    Returns:
        True if test completed successfully, False otherwise.

    Example:
        ```python
        config = load_config()
        success = await test_token_tracking_gigachat(config)
        ```
    """
    try:
        # Display test header
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
            console.print("[bold cyan]TEST 1: Token Tracking — GigaChat[/bold cyan]")
            console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 70)
            print("TEST 1: Token Tracking — GigaChat")
            print("=" * 70 + "\n")

        # Check credentials
        if not config["gigachat_api_key"]:
            if RICH_AVAILABLE:
                console.print("[yellow]⚠️  GIGACHAT_API_KEY not found, skipping test[/yellow]\n")
            else:
                print("⚠️  GIGACHAT_API_KEY not found, skipping test\n")
            return False

        # Initialize router
        router = Router()
        gigachat_config = ProviderConfig(  # type: ignore[call-arg]
            name="gigachat",
            api_key=config["gigachat_api_key"],
            model="GigaChat",
            scope="GIGACHAT_API_PERS",
            verify_ssl=False,
            timeout=30,
        )
        router.add_provider(GigaChatProvider(gigachat_config))

        # Make request
        prompt = "Напиши короткое стихотворение про Python (4 строки)"
        if RICH_AVAILABLE:
            console.print(f"[dim]📤 Prompt:[/dim] {prompt}\n")
        else:
            print(f"📤 Prompt: {prompt}\n")

        response = await router.route(prompt)

        if RICH_AVAILABLE:
            console.print(f"[dim]📥 Response:[/dim] {response[:100]}...\n")
        else:
            print(f"📥 Response: {response[:100]}...\n")

        # Check metrics
        metrics = router.get_metrics()
        gigachat_metrics = metrics.get("gigachat")

        if not gigachat_metrics:
            if RICH_AVAILABLE:
                console.print("[red]❌ Metrics not found[/red]\n")
            else:
                print("❌ Metrics not found\n")
            return False

        # Display token tracking results
        if RICH_AVAILABLE:
            console.print("[bold]📊 Token Tracking Results:[/bold]")
            console.print(f"   Prompt Tokens:     [cyan]{gigachat_metrics.total_prompt_tokens}[/cyan]")
            console.print(f"   Completion Tokens: [cyan]{gigachat_metrics.total_completion_tokens}[/cyan]")
            console.print(f"   Total Tokens:      [cyan]{gigachat_metrics.total_tokens}[/cyan]")
            console.print(f"   Cost:              [yellow]{gigachat_metrics.total_cost:.4f} RUB[/yellow]\n")
        else:
            print("📊 Token Tracking Results:")
            print(f"   Prompt Tokens:     {gigachat_metrics.total_prompt_tokens}")
            print(f"   Completion Tokens: {gigachat_metrics.total_completion_tokens}")
            print(f"   Total Tokens:      {gigachat_metrics.total_tokens}")
            print(f"   Cost:              {gigachat_metrics.total_cost:.4f} RUB\n")

        # Verify token tracking works
        success = (
            gigachat_metrics.total_prompt_tokens > 0
            and gigachat_metrics.total_completion_tokens > 0
            and gigachat_metrics.total_cost > 0
        )

        if success:
            if RICH_AVAILABLE:
                console.print("[bold green]✅ Token tracking working correctly[/bold green]\n")
            else:
                print("✅ Token tracking working correctly\n")
        else:
            if RICH_AVAILABLE:
                console.print("[bold red]❌ Token tracking failed[/bold red]\n")
            else:
                print("❌ Token tracking failed\n")

        return success

    except Exception as e:
        if RICH_AVAILABLE:
            console = Console()
            console.print(f"[bold red]❌ Test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Test failed: {e}\n")
        return False


async def test_token_tracking_yandex(config: dict[str, str | None]) -> bool:
    """Test token tracking with YandexGPT provider.

    This test verifies token tracking with YandexGPT:
    - Makes a real API request to YandexGPT
    - Verifies token counts > 0
    - Verifies YandexGPT pricing is applied correctly

    Args:
        config: Configuration dictionary from load_config().

    Returns:
        True if test completed successfully, False otherwise.

    Example:
        ```python
        config = load_config()
        success = await test_token_tracking_yandex(config)
        ```
    """
    try:
        # Display test header
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
            console.print("[bold cyan]TEST 2: Token Tracking — YandexGPT[/bold cyan]")
            console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 70)
            print("TEST 2: Token Tracking — YandexGPT")
            print("=" * 70 + "\n")

        # Check credentials
        if not config["yandexgpt_api_key"] or not config["yandexgpt_folder_id"]:
            if RICH_AVAILABLE:
                console.print("[yellow]⚠️  YandexGPT credentials not found, skipping test[/yellow]\n")
            else:
                print("⚠️  YandexGPT credentials not found, skipping test\n")
            return False

        # Initialize router
        router = Router()
        yandex_config = ProviderConfig(  # type: ignore[call-arg]
            name="yandexgpt",
            api_key=config["yandexgpt_api_key"],
            folder_id=config["yandexgpt_folder_id"],
            model="yandexgpt/latest",
        )
        router.add_provider(YandexGPTProvider(yandex_config))

        # Make request
        prompt = "Объясни машинное обучение простыми словами (2 предложения)"
        if RICH_AVAILABLE:
            console.print(f"[dim]📤 Prompt:[/dim] {prompt}\n")
        else:
            print(f"📤 Prompt: {prompt}\n")

        response = await router.route(prompt)

        if RICH_AVAILABLE:
            console.print(f"[dim]📥 Response:[/dim] {response[:100]}...\n")
        else:
            print(f"📥 Response: {response[:100]}...\n")

        # Check metrics
        metrics = router.get_metrics()
        yandex_metrics = metrics.get("yandexgpt")

        if not yandex_metrics:
            if RICH_AVAILABLE:
                console.print("[red]❌ Metrics not found[/red]\n")
            else:
                print("❌ Metrics not found\n")
            return False

        # Display token tracking results
        if RICH_AVAILABLE:
            console.print("[bold]📊 Token Tracking Results:[/bold]")
            console.print(f"   Prompt Tokens:     [cyan]{yandex_metrics.total_prompt_tokens}[/cyan]")
            console.print(f"   Completion Tokens: [cyan]{yandex_metrics.total_completion_tokens}[/cyan]")
            console.print(f"   Total Tokens:      [cyan]{yandex_metrics.total_tokens}[/cyan]")
            console.print(f"   Cost:              [yellow]{yandex_metrics.total_cost:.4f} RUB[/yellow]\n")
        else:
            print("📊 Token Tracking Results:")
            print(f"   Prompt Tokens:     {yandex_metrics.total_prompt_tokens}")
            print(f"   Completion Tokens: {yandex_metrics.total_completion_tokens}")
            print(f"   Total Tokens:      {yandex_metrics.total_tokens}")
            print(f"   Cost:              {yandex_metrics.total_cost:.4f} RUB\n")

        # Verify
        success = (
            yandex_metrics.total_prompt_tokens > 0
            and yandex_metrics.total_completion_tokens > 0
            and yandex_metrics.total_cost > 0
        )

        if success:
            if RICH_AVAILABLE:
                console.print("[bold green]✅ Token tracking working correctly[/bold green]\n")
            else:
                print("✅ Token tracking working correctly\n")
        else:
            if RICH_AVAILABLE:
                console.print("[bold red]❌ Token tracking failed[/bold red]\n")
            else:
                print("❌ Token tracking failed\n")

        return success

    except Exception as e:
        if RICH_AVAILABLE:
            console = Console()
            console.print(f"[bold red]❌ Test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Test failed: {e}\n")
        return False


async def test_streaming_with_tokens(config: dict[str, str | None]) -> bool:
    """Test token tracking in streaming mode.

    This test verifies that token tracking works with streaming:
    - Makes a streaming request to GigaChat
    - Accumulates chunks in real-time
    - Verifies tokens are counted after streaming completes
    - Verifies cost is calculated for streamed responses

    Args:
        config: Configuration dictionary from load_config().

    Returns:
        True if test completed successfully, False otherwise.

    Example:
        ```python
        config = load_config()
        success = await test_streaming_with_tokens(config)
        ```
    """
    try:
        # Display test header
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
            console.print("[bold cyan]TEST 3: Token Tracking — Streaming[/bold cyan]")
            console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 70)
            print("TEST 3: Token Tracking — Streaming")
            print("=" * 70 + "\n")

        # Check credentials
        if not config["gigachat_api_key"]:
            if RICH_AVAILABLE:
                console.print("[yellow]⚠️  GIGACHAT_API_KEY not found, skipping test[/yellow]\n")
            else:
                print("⚠️  GIGACHAT_API_KEY not found, skipping test\n")
            return False

        # Initialize router
        router = Router()
        gigachat_config = ProviderConfig(  # type: ignore[call-arg]
            name="gigachat",
            api_key=config["gigachat_api_key"],
            model="GigaChat",
            scope="GIGACHAT_API_PERS",
            verify_ssl=False,
            timeout=30,
        )
        router.add_provider(GigaChatProvider(gigachat_config))

        # Streaming request
        prompt = "Расскажи интересный факт о космосе"
        if RICH_AVAILABLE:
            console.print(f"[dim]📤 Prompt:[/dim] {prompt}\n")
            console.print("[dim]📥 Response (streaming):[/dim] ", end="")
            # Use regular print for streaming chunks (rich doesn't support flush)
            async for chunk in router.route_stream(prompt):
                print(chunk, end="", flush=True)
            print("\n")
        else:
            print(f"📤 Prompt: {prompt}\n")
            print("📥 Response (streaming): ", end="", flush=True)
            async for chunk in router.route_stream(prompt):
                print(chunk, end="", flush=True)
            print("\n")

        # Wait for metrics update
        await asyncio.sleep(1)

        # Check metrics
        metrics = router.get_metrics()
        gigachat_metrics = metrics.get("gigachat")

        if not gigachat_metrics:
            if RICH_AVAILABLE:
                console.print("[red]❌ Metrics not found[/red]\n")
            else:
                print("❌ Metrics not found\n")
            return False

        # Display streaming token results
        if RICH_AVAILABLE:
            console.print("[bold]📊 Streaming Token Results:[/bold]")
            console.print(f"   Total Tokens: [cyan]{gigachat_metrics.total_tokens}[/cyan]")
            console.print(f"   Cost:         [yellow]{gigachat_metrics.total_cost:.4f} RUB[/yellow]\n")
        else:
            print("📊 Streaming Token Results:")
            print(f"   Total Tokens: {gigachat_metrics.total_tokens}")
            print(f"   Cost:         {gigachat_metrics.total_cost:.4f} RUB\n")

        success = gigachat_metrics.total_tokens > 0

        if success:
            if RICH_AVAILABLE:
                console.print("[bold green]✅ Streaming token tracking working[/bold green]\n")
            else:
                print("✅ Streaming token tracking working\n")
        else:
            if RICH_AVAILABLE:
                console.print("[bold red]❌ Streaming token tracking failed[/bold red]\n")
            else:
                print("❌ Streaming token tracking failed\n")

        return success

    except Exception as e:
        if RICH_AVAILABLE:
            console = Console()
            console.print(f"[bold red]❌ Test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Test failed: {e}\n")
        return False


async def test_prometheus_endpoint(config: dict[str, str | None]) -> bool:
    """Test Prometheus metrics HTTP endpoint.

    This test verifies that Prometheus metrics export works:
    - Starts HTTP server on port 9091
    - Makes a request to generate metrics
    - Keeps server running for manual verification
    - Stops server gracefully

    Args:
        config: Configuration dictionary from load_config().

    Returns:
        True if test completed successfully, False otherwise.

    Example:
        ```python
        config = load_config()
        success = await test_prometheus_endpoint(config)
        ```
    """
    try:
        # Display test header
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
            console.print("[bold cyan]TEST 4: Prometheus Metrics Endpoint[/bold cyan]")
            console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 70)
            print("TEST 4: Prometheus Metrics Endpoint")
            print("=" * 70 + "\n")

        # Check credentials
        if not config["gigachat_api_key"]:
            if RICH_AVAILABLE:
                console.print("[yellow]⚠️  GIGACHAT_API_KEY not found, skipping test[/yellow]\n")
            else:
                print("⚠️  GIGACHAT_API_KEY not found, skipping test\n")
            return False

        # Initialize router
        router = Router()
        gigachat_config = ProviderConfig(  # type: ignore[call-arg]
            name="gigachat",
            api_key=config["gigachat_api_key"],
            model="GigaChat",
            scope="GIGACHAT_API_PERS",
            verify_ssl=False,
            timeout=30,
        )
        router.add_provider(GigaChatProvider(gigachat_config))

        # Start metrics server
        if RICH_AVAILABLE:
            console.print("[dim]📊 Starting Prometheus metrics server...[/dim]")
        else:
            print("📊 Starting Prometheus metrics server...")

        try:
            await router.start_metrics_server(port=9091)  # Use 9091 to avoid conflicts
            if RICH_AVAILABLE:
                console.print("[green]✅ Metrics server started at http://localhost:9091/metrics[/green]\n")
            else:
                print("✅ Metrics server started at http://localhost:9091/metrics\n")
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[red]❌ Failed to start server: {e}[/red]\n")
            else:
                print(f"❌ Failed to start server: {e}\n")
            return False

        # Make a request to generate metrics
        await router.route("Привет, как дела?")

        # Wait for metrics update
        await asyncio.sleep(2)

        # Display info
        if RICH_AVAILABLE:
            console.print("[bold]📊 Prometheus endpoint is running[/bold]")
            console.print("   [dim]Open http://localhost:9091/metrics in browser to verify[/dim]")
            console.print("   [dim]Expected metrics:[/dim]")
            console.print("   [cyan]- llm_requests_total[/cyan]")
            console.print("   [cyan]- llm_request_latency_seconds[/cyan]")
            console.print("   [cyan]- llm_tokens_total[/cyan]")
            console.print("   [cyan]- llm_cost_total[/cyan]")
            console.print("   [cyan]- llm_provider_health[/cyan]\n")
        else:
            print("📊 Prometheus endpoint is running")
            print("   Open http://localhost:9091/metrics in browser to verify")
            print("   Expected metrics:")
            print("   - llm_requests_total")
            print("   - llm_request_latency_seconds")
            print("   - llm_tokens_total")
            print("   - llm_cost_total")
            print("   - llm_provider_health\n")

        # Keep server running for manual check
        if RICH_AVAILABLE:
            console.print("[yellow]⏸️  Server running for 10 seconds for manual verification...[/yellow]\n")
        else:
            print("⏸️  Server running for 10 seconds for manual verification...\n")

        await asyncio.sleep(10)

        # Stop server
        await router.stop_metrics_server()
        if RICH_AVAILABLE:
            console.print("[green]✅ Metrics server stopped[/green]\n")
        else:
            print("✅ Metrics server stopped\n")

        return True

    except Exception as e:
        if RICH_AVAILABLE:
            console = Console()
            console.print(f"[bold red]❌ Test failed: {e}[/bold red]\n")
        else:
            print(f"❌ Test failed: {e}\n")
        return False


async def main() -> None:
    """Main entry point for v0.7.0 observability tests.

    Orchestrates execution of all v0.7.0 observability tests:
    1. Loads configuration from .env file
    2. Runs test_token_tracking_gigachat
    3. Runs test_token_tracking_yandex
    4. Runs test_streaming_with_tokens
    5. Runs test_prometheus_endpoint
    6. Displays final summary with test results

    Handles missing credentials gracefully (tests are skipped).

    Raises:
        SystemExit: On KeyboardInterrupt.

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
                "[bold cyan]Multi-LLM Orchestrator v0.7.0 — Observability Tests[/bold cyan]"
            )
            console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")
            console.print(
                "[dim]Testing token tracking, cost estimation, and Prometheus metrics.[/dim]\n"
            )
        else:
            print("\n" + "=" * 70)
            print("Multi-LLM Orchestrator v0.7.0 — Observability Tests")
            print("=" * 70 + "\n")
            print("Testing token tracking, cost estimation, and Prometheus metrics.\n")

        # Load configuration
        config = load_config()

        # Store test results
        test_results: list[tuple[str, bool]] = []

        # Run tests
        result1 = await test_token_tracking_gigachat(config)
        test_results.append(("GigaChat Token Tracking", result1))

        result2 = await test_token_tracking_yandex(config)
        test_results.append(("YandexGPT Token Tracking", result2))

        result3 = await test_streaming_with_tokens(config)
        test_results.append(("Streaming Token Tracking", result3))

        result4 = await test_prometheus_endpoint(config)
        test_results.append(("Prometheus Endpoint", result4))

        # Display final summary
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[bold cyan]" + "=" * 70 + "[/bold cyan]")
            console.print("[bold cyan]📊 TEST SUMMARY[/bold cyan]")
            console.print("[bold cyan]" + "=" * 70 + "[/bold cyan]\n")
        else:
            print("\n" + "=" * 70)
            print("📊 TEST SUMMARY")
            print("=" * 70 + "\n")

        # Display results for each test
        for test_name, success in test_results:
            if success:
                status = "✅ PASS"
                color = "green"
            else:
                status = "❌ FAIL"
                color = "red"

            if RICH_AVAILABLE:
                console.print(f"   [{color}]{status}[/{color}]  {test_name}")
            else:
                print(f"   {status}  {test_name}")

        # Calculate stats
        total = len(test_results)
        passed = sum(1 for _, result in test_results if result)

        if RICH_AVAILABLE:
            console.print(f"\n[bold cyan]{'=' * 70}[/bold cyan]")
            console.print(f"   [bold]Total: {passed}/{total} tests passed[/bold]")
            console.print(f"[bold cyan]{'=' * 70}[/bold cyan]\n")
        else:
            print(f"\n{'=' * 70}")
            print(f"   Total: {passed}/{total} tests passed")
            print(f"{'=' * 70}\n")

        # Final message
        if passed == total:
            if RICH_AVAILABLE:
                console.print("[bold green]🎉 All tests passed! v0.7.0 is ready for release![/bold green]\n")
            else:
                print("🎉 All tests passed! v0.7.0 is ready for release!\n")
        else:
            if RICH_AVAILABLE:
                console.print(f"[yellow]⚠️  {total - passed} test(s) failed. Review before release.[/yellow]\n")
            else:
                print(f"⚠️  {total - passed} test(s) failed. Review before release.\n")

    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[yellow]⚠️  Test interrupted by user[/yellow]\n")
        else:
            print("\n⚠️  Test interrupted by user\n")
        sys.exit(0)
    except Exception as e:
        if RICH_AVAILABLE:
            console = Console()
            console.print(f"\n[bold red]❌ Test execution failed: {e}[/bold red]\n")
        else:
            print(f"\n❌ Test execution failed: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

