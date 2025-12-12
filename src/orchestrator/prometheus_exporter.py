"""Prometheus metrics exporter for Multi-LLM Orchestrator.

This module provides HTTP server for exposing Prometheus metrics via
/metrics endpoint, allowing integration with Prometheus monitoring systems.

Example:
    ```python
    from orchestrator.prometheus_exporter import PrometheusExporter
    from orchestrator.metrics import ProviderMetrics

    # Initialize exporter
    exporter = PrometheusExporter(port=9090)

    # Start HTTP server
    await exporter.start()

    # Update metrics
    metrics_dict = {"provider-1": ProviderMetrics()}
    exporter.update_metrics(metrics_dict)

    # Metrics available at http://localhost:9090/metrics

    # Stop server
    await exporter.stop()
    ```
"""

import logging
from typing import Any

from aiohttp import web
from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger("orchestrator.prometheus")

# Prometheus metric definitions
# Note: These are module-level singletons (prometheus_client pattern)

REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total number of LLM requests",
    ["provider", "status"],
)

REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "Latency of LLM requests in seconds",
    ["provider"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")],
)

TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total tokens processed",
    ["provider", "type"],  # type = "prompt" or "completion"
)

COST_TOTAL = Counter(
    "llm_cost_total",
    "Total cost in rubles",
    ["provider"],
)

PROVIDER_HEALTH = Gauge(
    "llm_provider_health",
    "Provider health status (1=healthy, 0.5=degraded, 0=unhealthy)",
    ["provider"],
)


class PrometheusExporter:
    """Prometheus metrics exporter with HTTP server.

    This class provides an HTTP server that exposes Prometheus metrics
    at /metrics endpoint. It updates metrics based on ProviderMetrics
    data from the Router.

    Attributes:
        port: HTTP server port
        app: aiohttp application
        runner: aiohttp runner for server lifecycle
        site: aiohttp TCP site for binding to port

    Example:
        ```python
        # Basic usage
        exporter = PrometheusExporter(port=9090)
        await exporter.start()

        # Update metrics
        metrics_dict = router.get_metrics()
        exporter.update_metrics(metrics_dict)

        # Metrics available at http://localhost:9090/metrics
        await exporter.stop()
        ```
    """

    def __init__(self, port: int = 9090) -> None:
        """Initialize Prometheus exporter.

        Args:
            port: HTTP server port (default: 9090).
                 Standard Prometheus port is 9090, but can be customized
                 if multiple exporters run on the same machine.

        Example:
            ```python
            # Default port
            exporter = PrometheusExporter()

            # Custom port
            exporter = PrometheusExporter(port=9091)
            ```
        """
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/metrics", self._metrics_handler)
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """Handle GET /metrics endpoint.

        This handler generates Prometheus text format output from the
        global REGISTRY containing all registered metrics.

        Args:
            request: aiohttp request object (unused, required by aiohttp signature)

        Returns:
            HTTP response with Prometheus text format metrics

        Note:
            This is an internal method called by aiohttp. It should not
            be called directly by users.
        """
        try:
            # Generate Prometheus format (returns bytes)
            metrics_output = generate_latest(REGISTRY)

            # Return as Response with correct content type
            return web.Response(
                body=metrics_output,
                content_type="text/plain; version=0.0.4",  # Charset removed from here
                charset="utf-8",  # Charset specified only here
            )
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return web.Response(
                text=f"Error generating metrics: {e}",
                status=500,
            )

    async def start(self) -> None:
        """Start HTTP server (non-blocking).

        The server runs in the background and serves /metrics endpoint.
        This method is async and non-blocking, allowing the main application
        to continue running.

        Raises:
            OSError: If port is already in use or cannot bind to port.
                    Common error: "Address already in use" when port is occupied.

        Example:
            ```python
            exporter = PrometheusExporter(port=9090)

            try:
                await exporter.start()
                print("Metrics server started at http://localhost:9090/metrics")
            except OSError as e:
                print(f"Failed to start server: {e}")
                # Try different port
                exporter = PrometheusExporter(port=9091)
                await exporter.start()
            ```
        """
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()
            logger.info(
                f"Prometheus metrics server started on http://0.0.0.0:{self.port}/metrics"
            )
        except OSError as e:
            if "Address already in use" in str(e):
                raise OSError(
                    f"Port {self.port} is already in use. "
                    "Choose a different port or stop the conflicting service. "
                    f"Original error: {e}"
                ) from e
            raise

    async def stop(self) -> None:
        """Stop HTTP server gracefully.

        Performs graceful shutdown of the HTTP server, cleaning up all
        resources. Safe to call even if server is not running.

        Example:
            ```python
            exporter = PrometheusExporter()
            await exporter.start()

            # ... do work ...

            # Cleanup
            await exporter.stop()
            ```
        """
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Prometheus metrics server stopped")

    def update_metrics(self, metrics_dict: dict[str, Any]) -> None:
        """Update Prometheus metrics from ProviderMetrics.

        This method reads ProviderMetrics objects and updates the global
        Prometheus metrics (counters, gauges, histograms). It should be
        called periodically to keep metrics up-to-date.

        Args:
            metrics_dict: Dictionary mapping provider name to ProviderMetrics.
                         Typically obtained from Router.get_metrics().

        Example:
            ```python
            # Get metrics from router
            metrics_dict = router.get_metrics()

            # Update Prometheus exporter
            exporter.update_metrics(metrics_dict)

            # Metrics are now available at /metrics endpoint
            ```

        Note:
            This method directly sets Counter values, which is a special
            operation supported by prometheus_client for exporting external
            metrics. Normal Counter usage would use .inc() instead.
        """
        for provider_name, provider_metrics in metrics_dict.items():
            # Update request counters
            # Note: Using _value.set() for Counters is special for exporters
            # Normal usage would be .inc(), but we're syncing external metrics
            REQUESTS_TOTAL.labels(
                provider=provider_name, status="success"
            )._value.set(provider_metrics.successful_requests)

            REQUESTS_TOTAL.labels(
                provider=provider_name, status="failure"
            )._value.set(provider_metrics.failed_requests)

            # Update token counters
            TOKENS_TOTAL.labels(provider=provider_name, type="prompt")._value.set(
                provider_metrics.total_prompt_tokens
            )

            TOKENS_TOTAL.labels(
                provider=provider_name, type="completion"
            )._value.set(provider_metrics.total_completion_tokens)

            # Update cost counter
            COST_TOTAL.labels(provider=provider_name)._value.set(
                provider_metrics.total_cost
            )

            # Update health gauge (convert health status to numeric value)
            health_value = {
                "healthy": 1.0,
                "degraded": 0.5,
                "unhealthy": 0.0,
            }.get(provider_metrics.health_status, 0.0)

            PROVIDER_HEALTH.labels(provider=provider_name).set(health_value)

            # Update latency histogram
            # Note: For histogram, we observe individual latencies
            # Here we use average latency as approximation (not ideal but simple)
            if provider_metrics.avg_latency_ms > 0:
                avg_latency_seconds = provider_metrics.avg_latency_ms / 1000.0
                # Clear previous observations and add current average
                # This is a simplified approach - ideally we'd track individual observations
                REQUEST_LATENCY.labels(provider=provider_name).observe(
                    avg_latency_seconds
                )

