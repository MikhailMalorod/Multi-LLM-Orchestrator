"""Prometheus Integration Demo

This example demonstrates:
1. Starting Prometheus metrics server
2. Making LLM requests with multiple providers
3. Accessing metrics programmatically
4. Viewing metrics via HTTP endpoint

Prerequisites:
    - Install dependencies: pip install multi-llm-orchestrator
    - (Optional) Install Prometheus for scraping

Run:
    python examples/prometheus_demo.py

Then visit: http://localhost:9090/metrics
"""

import asyncio

from orchestrator import Router
from orchestrator.providers import MockProvider, ProviderConfig


async def main() -> None:
    print("🚀 Multi-LLM Orchestrator — Prometheus Integration Demo\n")

    # Initialize router with best-available strategy
    router = Router(strategy="best-available")

    # Add multiple mock providers
    print("📦 Adding providers...")
    for i in range(3):
        config = ProviderConfig(
            name=f"mock-{i+1}",  # Unique names: mock-1, mock-2, mock-3
            model="mock-normal"
        )
        router.add_provider(MockProvider(config))
    print(f"✅ Added {len(router.providers)} providers\n")

    # Start Prometheus metrics server
    print("📊 Starting Prometheus metrics server...")
    try:
        await router.start_metrics_server(port=9090)
        print("✅ Metrics server running at: http://localhost:9090/metrics\n")
    except OSError as e:
        if "already in use" in str(e):
            print("⚠️  Port 9090 already in use. Trying port 9091...")
            await router.start_metrics_server(port=9091)
            print("✅ Metrics server running at: http://localhost:9091/metrics\n")
        else:
            raise

    # Make some requests to generate metrics
    print("📤 Making 10 requests to generate metrics...")
    for i in range(10):
        prompt = f"Request {i+1}: Tell me about Python programming."
        response = await router.route(prompt)
        print(f"  [{i+1}/10] Response: {len(response)} chars, {response.split()[0:3]}")

    print("\n✅ All requests completed\n")

    # Wait for metrics to update (background task runs every 1 second)
    print("⏳ Waiting for metrics update...")
    await asyncio.sleep(2)
    print("✅ Metrics updated\n")

    # Access and display metrics programmatically
    print("=" * 70)
    print("📈 PROVIDER METRICS SUMMARY")
    print("=" * 70)

    metrics = router.get_metrics()
    for provider_name, provider_metrics in metrics.items():
        print(f"\n🔹 {provider_name.upper()}")
        print(f"   Total Requests:       {provider_metrics.total_requests}")
        print(f"   ├─ Successful:        {provider_metrics.successful_requests}")
        print(f"   └─ Failed:            {provider_metrics.failed_requests}")
        print(f"   Success Rate:         {provider_metrics.success_rate:.1%}")
        print(f"   Avg Latency:          {provider_metrics.avg_latency_ms:.1f} ms")
        print(f"   Health Status:        {provider_metrics.health_status.upper()}")
        print("   ")
        print("   Token Usage:")
        print(f"   ├─ Prompt Tokens:     {provider_metrics.total_prompt_tokens:,}")
        print(f"   ├─ Completion Tokens: {provider_metrics.total_completion_tokens:,}")
        print(f"   └─ Total Tokens:      {provider_metrics.total_tokens:,}")
        print("   ")
        print(f"   💰 Total Cost:        {provider_metrics.total_cost:.2f} RUB")

    # Calculate totals across all providers
    total_requests = sum(m.total_requests for m in metrics.values())
    total_tokens = sum(m.total_tokens for m in metrics.values())
    total_cost = sum(m.total_cost for m in metrics.values())

    print("\n" + "=" * 70)
    print("📊 AGGREGATE STATISTICS")
    print("=" * 70)
    print(f"   Total Requests:       {total_requests}")
    print(f"   Total Tokens:         {total_tokens:,}")
    print(f"   Total Cost:           {total_cost:.2f} RUB")
    print("=" * 70 + "\n")

    # Display Prometheus endpoint info
    print("📊 PROMETHEUS METRICS ENDPOINT")
    print("-" * 70)
    print("   URL:     http://localhost:9090/metrics")
    print("   Format:  Prometheus text format")
    print("")
    print("   Available metrics:")
    print("   • llm_requests_total              - Request counts by status")
    print("   • llm_request_latency_seconds     - Latency histogram")
    print("   • llm_tokens_total                - Token counts by type")
    print("   • llm_cost_total                  - Cost in RUB")
    print("   • llm_provider_health             - Health status gauge")
    print("-" * 70 + "\n")

    # Prometheus query examples
    print("🔍 EXAMPLE PROMETHEUS QUERIES")
    print("-" * 70)
    print("   # Request rate (requests/sec)")
    print("   rate(llm_requests_total[5m])")
    print("")
    print("   # Success rate (%)")
    print("   sum(rate(llm_requests_total{status=\"success\"}[5m])) /")
    print("   sum(rate(llm_requests_total[5m])) * 100")
    print("")
    print("   # Average latency (seconds)")
    print("   rate(llm_request_latency_seconds_sum[5m]) /")
    print("   rate(llm_request_latency_seconds_count[5m])")
    print("")
    print("   # Total cost per provider (RUB)")
    print("   llm_cost_total")
    print("")
    print("   # Tokens per second")
    print("   rate(llm_tokens_total[5m])")
    print("")
    print("   # Unhealthy providers")
    print("   llm_provider_health < 1.0")
    print("-" * 70 + "\n")

    # Prometheus configuration example
    print("⚙️  PROMETHEUS CONFIGURATION")
    print("-" * 70)
    print("   Add this to your prometheus.yml:")
    print("")
    print("   scrape_configs:")
    print("     - job_name: 'llm-orchestrator'")
    print("       static_configs:")
    print("         - targets: ['localhost:9090']")
    print("       scrape_interval: 15s")
    print("")
    print("   Then restart Prometheus:")
    print("   $ prometheus --config.file=prometheus.yml")
    print("-" * 70 + "\n")

    # Keep server running
    print("⏸️  Server is running. Press Ctrl+C to stop...\n")

    try:
        # Keep the server running indefinitely
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping metrics server...")
        await router.stop_metrics_server()
        print("✅ Metrics server stopped")
        print("\n👋 Demo completed! Thank you for using Multi-LLM Orchestrator.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
