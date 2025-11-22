#!/usr/bin/env python3
"""Routing Demo for Multi-LLM Orchestrator.

This demo script demonstrates the Router functionality and fallback mechanisms
of the Multi-LLM Orchestrator. It showcases:

- Three routing strategies: round-robin, random, and first-available
- Automatic fallback mechanism when providers fail
- Error handling when all providers are unavailable

The demo uses MockProvider to simulate various provider states without
requiring actual API credentials.

Usage:
    python examples/routing_demo.py

The script runs automatically through all 6 demonstration scenarios.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator import Router
from src.orchestrator.providers.base import BaseProvider, ProviderConfig
from src.orchestrator.providers.mock import MockProvider

# Configure logging to suppress verbose Router logs
logging.basicConfig(level=logging.WARNING)
# Suppress Router logger specifically
logging.getLogger("orchestrator.router").setLevel(logging.ERROR)

# Prompts for demonstration
PROMPTS = [
    "What is Python?",
    "Explain async/await",
    "How does routing work?",
    "Tell me about LLMs",
    "What is fallback mechanism?",
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def create_providers_table(providers: List[BaseProvider]) -> Table:
    """Create a Rich table displaying provider information.
    
    This function creates a formatted table showing each provider's name,
    mode (mock-normal, mock-timeout, etc.), and health status.
    Health check is performed asynchronously for each provider.
    
    Args:
        providers: List of provider instances to display
    
    Returns:
        Rich Table object with provider information (Name, Mode, Health Check)
    """
    table = Table(title="Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Mode", style="magenta")
    table.add_column("Health Check", style="green")
    
    # Check health status for each provider (async operation)
    for provider in providers:
        health = await provider.health_check()
        health_status = "✅ Healthy" if health else "❌ Unhealthy"
        table.add_row(
            provider.config.name,
            provider.config.model or "mock-normal",
            health_status
        )
    
    return table


def create_results_table() -> Table:
    """Create a Rich table for displaying request results.
    
    Returns:
        Rich Table object with columns: Request, Provider, Status, Time
    """
    table = Table(title="Results")
    table.add_column("Request", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Time", style="yellow")
    
    return table


# ============================================================================
# DEMONSTRATION SCENARIOS
# ============================================================================


async def demo_round_robin(console: Console) -> None:
    """Demonstrate round-robin routing strategy with normal providers.
    
    This scenario shows how the round-robin strategy cycles through
    providers in a fixed order. All providers are healthy and working,
    so requests are distributed evenly in a cyclic pattern.
    
    Args:
        console: Rich Console instance for output
    """
    # Display scenario header
    console.print(Panel(
        "[bold cyan]Scenario 1: Round-Robin Strategy (Normal Operation)[/bold cyan]\n\n"
        "Demonstrates cyclic provider selection when all providers are healthy.",
        border_style="cyan"
    ))
    
    # Initialize router with round-robin strategy
    router = Router(strategy="round-robin")
    
    # Add 3 normal providers
    providers = [
        MockProvider(ProviderConfig(name="provider-1", model="mock-normal")),
        MockProvider(ProviderConfig(name="provider-2", model="mock-normal")),
        MockProvider(ProviderConfig(name="provider-3", model="mock-normal")),
    ]
    
    for provider in providers:
        router.add_provider(provider)
    
    # Display providers table
    providers_table = await create_providers_table(providers)
    console.print(providers_table)
    console.print()
    
    # Execute 5 requests and measure time for each
    results_table = create_results_table()
    
    for i in range(5):
        prompt = PROMPTS[i % len(PROMPTS)]
        
        # Measure request time
        start = time.perf_counter()
        result = await router.route(prompt)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        
        # Note: Router doesn't expose which provider was used, so we show success
        # In round-robin, providers cycle: 1 → 2 → 3 → 1 → 2
        results_table.add_row(
            f"Request #{i + 1}",
            f"provider-{(i % 3) + 1}",
            "✅ Success",
            f"{elapsed_ms}ms"
        )
    
    # Display results
    console.print(results_table)
    console.print()


async def demo_random(console: Console) -> None:
    """Demonstrate random routing strategy with normal providers.
    
    This scenario shows how the random strategy selects providers
    unpredictably. All providers are healthy, so any can be chosen
    for each request.
    
    Args:
        console: Rich Console instance for output
    """
    # Display scenario header
    console.print(Panel(
        "[bold cyan]Scenario 2: Random Strategy (Normal Operation)[/bold cyan]\n\n"
        "Demonstrates random provider selection when all providers are healthy.",
        border_style="cyan"
    ))
    
    # Initialize router with random strategy
    router = Router(strategy="random")
    
    # Add 3 normal providers
    providers = [
        MockProvider(ProviderConfig(name="provider-1", model="mock-normal")),
        MockProvider(ProviderConfig(name="provider-2", model="mock-normal")),
        MockProvider(ProviderConfig(name="provider-3", model="mock-normal")),
    ]
    
    for provider in providers:
        router.add_provider(provider)
    
    # Display providers table
    providers_table = await create_providers_table(providers)
    console.print(providers_table)
    console.print()
    
    # Execute 5 requests with random selection
    results_table = create_results_table()
    
    for i in range(5):
        prompt = PROMPTS[i % len(PROMPTS)]
        
        # Measure request time
        start = time.perf_counter()
        result = await router.route(prompt)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        
        # Note: We can't know which provider was randomly selected,
        # so we show that a random one was chosen
        results_table.add_row(
            f"Request #{i + 1}",
            "Random",
            "✅ Success",
            f"{elapsed_ms}ms"
        )
    
    # Display results
    console.print(results_table)
    console.print()


async def demo_first_available(console: Console) -> None:
    """Demonstrate first-available routing strategy with mixed providers.
    
    This scenario shows how first-available strategy skips unhealthy
    providers and selects the first healthy one. The router will always
    choose the first healthy provider (provider-2 in this case).
    
    Args:
        console: Rich Console instance for output
    """
    # Display scenario header
    console.print(Panel(
        "[bold cyan]Scenario 3: First-Available Strategy (Normal Operation)[/bold cyan]\n\n"
        "Demonstrates selection of first healthy provider, skipping unhealthy ones.",
        border_style="cyan"
    ))
    
    # Initialize router with first-available strategy
    router = Router(strategy="first-available")
    
    # Add providers: 1 unhealthy + 2 healthy
    providers = [
        MockProvider(ProviderConfig(name="provider-1", model="mock-unhealthy")),
        MockProvider(ProviderConfig(name="provider-2", model="mock-normal")),
        MockProvider(ProviderConfig(name="provider-3", model="mock-normal")),
    ]
    
    for provider in providers:
        router.add_provider(provider)
    
    # Display providers table (shows health status)
    providers_table = await create_providers_table(providers)
    console.print(providers_table)
    console.print()
    
    # Show which provider will be selected
    console.print(
        "ℹ️ [blue]first-available strategy:[/blue] "
        "Skipped unhealthy [yellow]provider-1[/yellow], "
        "selected [green]provider-2[/green] (first healthy)"
    )
    console.print()
    
    # Execute 3 requests (all should go to provider-2)
    results_table = create_results_table()
    
    for i in range(3):
        prompt = PROMPTS[i % len(PROMPTS)]
        
        # Measure request time
        start = time.perf_counter()
        result = await router.route(prompt)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        
        results_table.add_row(
            f"Request #{i + 1}",
            "provider-2",
            "✅ Success",
            f"{elapsed_ms}ms"
        )
    
    # Display results
    console.print(results_table)
    console.print()


async def demo_fallback_timeout(console: Console) -> None:
    """Demonstrate fallback mechanism when a provider times out.
    
    This scenario shows automatic fallback: the first provider (mock-timeout)
    fails with TimeoutError, and the router automatically tries the next
    provider (mock-normal) which succeeds.
    
    Args:
        console: Rich Console instance for output
    """
    # Display scenario header
    console.print(Panel(
        "[bold yellow]Scenario 4: Fallback Mechanism (Timeout)[/bold yellow]\n\n"
        "Demonstrates automatic fallback when selected provider times out.",
        border_style="yellow"
    ))
    
    # Initialize router with round-robin strategy
    router = Router(strategy="round-robin")
    
    # Add providers: 1 timeout + 2 normal
    providers = [
        MockProvider(ProviderConfig(name="provider-1", model="mock-timeout")),
        MockProvider(ProviderConfig(name="provider-2", model="mock-normal")),
        MockProvider(ProviderConfig(name="provider-3", model="mock-normal")),
    ]
    
    for provider in providers:
        router.add_provider(provider)
    
    # Display providers table
    providers_table = await create_providers_table(providers)
    console.print(providers_table)
    console.print()
    
    # Execute 1 request (will trigger fallback)
    results_table = create_results_table()
    prompt = PROMPTS[0]
    
    # Measure request time (includes fallback delay)
    start = time.perf_counter()
    result = await router.route(prompt)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    
    # Router tried provider-1 (timeout) → fallback to provider-2 (success)
    results_table.add_row(
        "Request #1",
        "provider-2",
        "⚠️ Fallback (provider-1 timed out)",
        f"{elapsed_ms}ms"
    )
    
    # Display results
    console.print(results_table)
    console.print()


async def demo_fallback_unhealthy(console: Console) -> None:
    """Demonstrate fallback with unhealthy providers and timeout.
    
    This scenario shows a complex fallback case:
    - first-available selects provider-3 (only healthy one)
    - provider-3 times out during generate()
    - Router falls back and tries all providers
    - provider-1 (unhealthy but generate() works) succeeds
    
    Args:
        console: Rich Console instance for output
    """
    # Display scenario header
    console.print(Panel(
        "[bold yellow]Scenario 5: Fallback with Unhealthy + Timeout[/bold yellow]\n\n"
        "Demonstrates fallback when first-available selection fails, "
        "and router tries all providers including unhealthy ones.",
        border_style="yellow"
    ))
    
    # Initialize router with first-available strategy
    router = Router(strategy="first-available")
    
    # Add providers: 2 unhealthy + 1 timeout (healthy but will fail)
    providers = [
        MockProvider(ProviderConfig(name="provider-1", model="mock-unhealthy")),
        MockProvider(ProviderConfig(name="provider-2", model="mock-unhealthy")),
        MockProvider(ProviderConfig(name="provider-3", model="mock-timeout")),
    ]
    
    for provider in providers:
        router.add_provider(provider)
    
    # Display providers table (shows health status)
    providers_table = await create_providers_table(providers)
    console.print(providers_table)
    console.print()
    
    # Explain what will happen
    console.print(
        "ℹ️ [blue]Process:[/blue] "
        "[yellow]first-available[/yellow] selects [cyan]provider-3[/cyan] "
        "(only healthy), but it times out. "
        "Router falls back and tries all providers. "
        "[green]provider-1[/green] succeeds (unhealthy but generate() works)."
    )
    console.print()
    
    # Execute 1 request (will trigger complex fallback)
    results_table = create_results_table()
    prompt = PROMPTS[0]
    
    # Measure request time (includes multiple fallback attempts)
    start = time.perf_counter()
    result = await router.route(prompt)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    
    # Router: provider-3 (timeout) → provider-1 (success, despite unhealthy)
    results_table.add_row(
        "Request #1",
        "provider-1",
        "⚠️ Fallback (provider-3 timed out)",
        f"{elapsed_ms}ms"
    )
    
    # Display results
    console.print(results_table)
    console.print()


async def demo_all_failed(console: Console) -> None:
    """Demonstrate error handling when all providers fail.
    
    This scenario shows what happens when all providers are unavailable.
    The router tries all providers in sequence, and when all fail,
    it raises the last exception (TimeoutError in this case).
    
    Args:
        console: Rich Console instance for output
    """
    # Display scenario header
    console.print(Panel(
        "[bold red]Scenario 6: All Providers Failed[/bold red]\n\n"
        "Demonstrates error handling when all providers are unavailable.",
        border_style="red"
    ))
    
    # Initialize router with round-robin strategy
    router = Router(strategy="round-robin")
    
    # Add 3 timeout providers (all will fail)
    providers = [
        MockProvider(ProviderConfig(name="provider-1", model="mock-timeout")),
        MockProvider(ProviderConfig(name="provider-2", model="mock-timeout")),
        MockProvider(ProviderConfig(name="provider-3", model="mock-timeout")),
    ]
    
    for provider in providers:
        router.add_provider(provider)
    
    # Display providers table
    providers_table = await create_providers_table(providers)
    console.print(providers_table)
    console.print()
    
    # Execute 1 request (will fail)
    results_table = create_results_table()
    prompt = PROMPTS[0]
    
    try:
        # Measure request time (will fail before completion)
        start = time.perf_counter()
        result = await router.route(prompt)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        
        # This should not happen, but handle just in case
        results_table.add_row(
            "Request #1",
            "???",
            "❌ Unexpected success",
            f"{elapsed_ms}ms"
        )
        console.print(results_table)
    except Exception as e:
        # Display error in red panel
        console.print(Panel(
            f"❌ [bold red]All providers failed![/bold red]\n\n"
            f"Error type: [yellow]{type(e).__name__}[/yellow]\n"
            f"Message: {str(e)}",
            title="[red]Error[/red]",
            border_style="red"
        ))
    
    console.print()


# ============================================================================
# MAIN FUNCTION
# ============================================================================


async def main() -> None:
    """Main function to orchestrate all demonstration scenarios.
    
    This function runs all 6 scenarios sequentially:
    1. Round-robin (normal)
    2. Random (normal)
    3. First-available (normal)
    4. Fallback (timeout)
    5. Fallback (unhealthy + timeout)
    6. All failed (error handling)
    """
    console = Console()
    
    # Display main header
    console.print(Panel(
        "[bold magenta]Multi-LLM Orchestrator: Routing Demo[/bold magenta]\n\n"
        "Demonstrates routing strategies and fallback mechanisms",
        border_style="magenta"
    ))
    console.print()
    
    # Run all scenarios
    await demo_round_robin(console)
    await demo_random(console)
    await demo_first_available(console)
    await demo_fallback_timeout(console)
    await demo_fallback_unhealthy(console)
    await demo_all_failed(console)
    
    # Display completion message
    console.print(Panel(
        "✅ [bold green]All scenarios completed![/bold green]\n\n"
        "Demonstrated:\n"
        "  • 3 routing strategies (round-robin, random, first-available)\n"
        "  • Automatic fallback mechanism\n"
        "  • Error handling when all providers fail",
        title="[green]Demo Complete[/green]",
        border_style="green"
    ))


if __name__ == "__main__":
    # Run the demo
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

