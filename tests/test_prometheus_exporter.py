"""Unit tests for Prometheus exporter.

This module tests Prometheus metrics exporter functionality including:
- /metrics endpoint charset handling
- Prometheus format validation
- HTTP response headers
"""

import pytest
from aiohttp.test_utils import make_mocked_request

from orchestrator.prometheus_exporter import PrometheusExporter


class TestPrometheusExporterMetricsEndpoint:
    """Test /metrics endpoint behavior."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_charset_utf8(self) -> None:
        """Test that /metrics endpoint returns proper UTF-8 charset."""
        exporter = PrometheusExporter(port=0)  # Port not used for handler test

        # Create a mock request
        request = make_mocked_request("GET", "/metrics")

        # Call the handler directly
        response = await exporter._metrics_handler(request)

        # Verify status code
        assert response.status == 200

        # Verify Content-Type header includes charset
        content_type = response.headers.get("Content-Type", "")
        assert "charset=utf-8" in content_type.lower()
        assert "text/plain" in content_type.lower()

        # Verify body is valid Prometheus format (contains HELP or TYPE)
        body_bytes = response.body
        assert body_bytes is not None
        body_text = body_bytes.decode("utf-8")
        assert "# HELP" in body_text or "# TYPE" in body_text

