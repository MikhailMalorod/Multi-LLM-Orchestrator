"""Unit tests for ProviderMetrics.

This module tests ProviderMetrics functionality including:
- Initial state
- record_success() and record_error()
- Computed properties (success_rate, avg_latency_ms, rolling_avg_latency_ms, recent_error_rate)
- Health status determination
- Error timestamp cleanup
"""

import pytest
from datetime import datetime, timedelta, timezone

from orchestrator.metrics import (
    ERROR_RATE_THRESHOLD_DEGRADED,
    ERROR_RATE_THRESHOLD_UNHEALTHY,
    LATENCY_THRESHOLD_FACTOR_DEGRADED,
    MIN_REQUESTS_FOR_HEALTH,
    MIN_REQUESTS_FOR_LATENCY_CHECK,
    ProviderMetrics,
)


class TestProviderMetricsInitialState:
    """Test ProviderMetrics initial state."""

    def test_metrics_initial_state(self) -> None:
        """Test that ProviderMetrics initializes with zero counters and empty collections."""
        metrics = ProviderMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.total_latency_ms == 0.0
        assert len(metrics._latency_window) == 0
        assert len(metrics._error_timestamps) == 0


class TestProviderMetricsRecordSuccess:
    """Test record_success() method."""

    def test_record_success(self) -> None:
        """Test that record_success() updates counters and adds to latency window."""
        metrics = ProviderMetrics()

        metrics.record_success(100.0)
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.failed_requests == 0
        assert metrics.total_latency_ms == 100.0
        assert len(metrics._latency_window) == 1
        assert metrics._latency_window[0] == 100.0

        metrics.record_success(200.0)
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 2
        assert metrics.total_latency_ms == 300.0
        assert len(metrics._latency_window) == 2

    def test_record_success_latency_window_limit(self) -> None:
        """Test that latency window is limited to LATENCY_WINDOW_SIZE."""
        metrics = ProviderMetrics()

        # Add more than LATENCY_WINDOW_SIZE requests
        for i in range(150):
            metrics.record_success(float(i))

        # Window should be limited to LATENCY_WINDOW_SIZE (100)
        assert len(metrics._latency_window) == 100
        # Should contain the last 100 values (50-149)
        assert metrics._latency_window[0] == 50.0
        assert metrics._latency_window[-1] == 149.0


class TestProviderMetricsRecordError:
    """Test record_error() method."""

    def test_record_error(self) -> None:
        """Test that record_error() updates counters and adds timestamp."""
        metrics = ProviderMetrics()
        now = datetime.now(timezone.utc)

        metrics.record_error(50.0, now)
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 1
        assert metrics.total_latency_ms == 0.0  # Not updated for errors
        assert len(metrics._error_timestamps) == 1
        assert metrics._error_timestamps[0] == now

    def test_record_error_cleanup_old_timestamps(self) -> None:
        """Test that record_error() cleans up old error timestamps."""
        metrics = ProviderMetrics()
        now = datetime.now(timezone.utc)

        # Add old error (more than 60 seconds ago)
        old_timestamp = now - timedelta(seconds=70)
        metrics.record_error(50.0, old_timestamp)

        # Add recent error
        recent_timestamp = now
        metrics.record_error(50.0, recent_timestamp)

        # Old error should be cleaned up
        assert len(metrics._error_timestamps) == 1
        assert metrics._error_timestamps[0] == recent_timestamp


class TestProviderMetricsComputedProperties:
    """Test computed properties of ProviderMetrics."""

    def test_success_rate(self) -> None:
        """Test success_rate calculation."""
        metrics = ProviderMetrics()

        # No requests
        assert metrics.success_rate == 0.0

        # All successful
        metrics.record_success(100.0)
        metrics.record_success(200.0)
        assert metrics.success_rate == 1.0

        # Mixed
        metrics.record_error(50.0, datetime.now(timezone.utc))
        assert metrics.success_rate == pytest.approx(2.0 / 3.0)

    def test_avg_latency_ms(self) -> None:
        """Test avg_latency_ms calculation (only for successful requests)."""
        metrics = ProviderMetrics()

        # No successful requests
        assert metrics.avg_latency_ms == 0.0

        # Only successful requests
        metrics.record_success(100.0)
        metrics.record_success(200.0)
        assert metrics.avg_latency_ms == 150.0

        # Errors don't affect avg_latency_ms
        metrics.record_error(50.0, datetime.now(timezone.utc))
        assert metrics.avg_latency_ms == 150.0  # Still 150.0

    def test_rolling_avg_latency_ms(self) -> None:
        """Test rolling_avg_latency_ms calculation."""
        metrics = ProviderMetrics()

        # Empty window
        assert metrics.rolling_avg_latency_ms is None

        # Single value
        metrics.record_success(100.0)
        assert metrics.rolling_avg_latency_ms == 100.0

        # Multiple values
        metrics.record_success(200.0)
        metrics.record_success(300.0)
        assert metrics.rolling_avg_latency_ms == 200.0  # (100+200+300)/3

    def test_recent_error_rate(self) -> None:
        """Test recent_error_rate calculation (simplified formula)."""
        metrics = ProviderMetrics()

        # No requests
        assert metrics.recent_error_rate == 0.0

        # All successful
        metrics.record_success(100.0)
        metrics.record_success(200.0)
        assert metrics.recent_error_rate == 0.0

        # With errors
        now = datetime.now(timezone.utc)
        metrics.record_error(50.0, now)
        metrics.record_error(50.0, now)
        # 2 errors out of 4 total requests
        assert metrics.recent_error_rate == pytest.approx(0.5)


class TestProviderMetricsHealthStatus:
    """Test health_status property."""

    def test_health_status_insufficient_data(self) -> None:
        """Test that health_status returns 'healthy' when insufficient data."""
        metrics = ProviderMetrics()

        # Less than MIN_REQUESTS_FOR_HEALTH
        for _ in range(MIN_REQUESTS_FOR_HEALTH - 1):
            metrics.record_success(100.0)

        assert metrics.health_status == "healthy"

    def test_health_status_unhealthy_by_error_rate(self) -> None:
        """Test that health_status returns 'unhealthy' for high error rate."""
        metrics = ProviderMetrics()
        now = datetime.now(timezone.utc)

        # Create enough requests
        for _ in range(MIN_REQUESTS_FOR_HEALTH):
            metrics.record_success(100.0)

        # Add enough errors to exceed UNHEALTHY threshold
        # recent_error_rate = len(_error_timestamps) / total_requests
        # We need: len(_error_timestamps) / total_requests >= 0.6
        # So: len(_error_timestamps) >= 0.6 * total_requests
        # After adding errors, total_requests will increase, so we need to account for that
        # Let's add enough errors to ensure the ratio is >= 0.6
        initial_total = metrics.total_requests
        # Add errors: we want errors / (initial_total + errors) >= 0.6
        # errors >= 0.6 * (initial_total + errors)
        # errors >= 0.6 * initial_total + 0.6 * errors
        # 0.4 * errors >= 0.6 * initial_total
        # errors >= 1.5 * initial_total
        errors_needed = int(1.5 * initial_total) + 1

        for _ in range(errors_needed):
            metrics.record_error(50.0, now)

        # Verify error rate
        error_rate = metrics.recent_error_rate
        assert error_rate >= ERROR_RATE_THRESHOLD_UNHEALTHY, f"Error rate {error_rate} should be >= {ERROR_RATE_THRESHOLD_UNHEALTHY}"
        assert metrics.health_status == "unhealthy"

    def test_health_status_degraded_by_error_rate(self) -> None:
        """Test that health_status returns 'degraded' for medium error rate."""
        metrics = ProviderMetrics()
        now = datetime.now(timezone.utc)

        # Create enough requests
        for _ in range(MIN_REQUESTS_FOR_HEALTH):
            metrics.record_success(100.0)

        # Add errors to exceed DEGRADED threshold but not UNHEALTHY
        # We want: 0.3 <= error_rate < 0.6
        # error_rate = errors / (initial_total + errors)
        # Let's add errors such that error_rate is around 0.4 (between thresholds)
        initial_total = metrics.total_requests
        # errors / (initial_total + errors) = 0.4
        # errors = 0.4 * (initial_total + errors)
        # errors = 0.4 * initial_total + 0.4 * errors
        # 0.6 * errors = 0.4 * initial_total
        # errors = (2/3) * initial_total
        errors_needed = int((2.0 / 3.0) * initial_total) + 1

        for _ in range(errors_needed):
            metrics.record_error(50.0, now)

        # Should be degraded (error rate between 0.3 and 0.6)
        status = metrics.health_status
        error_rate = metrics.recent_error_rate
        assert ERROR_RATE_THRESHOLD_DEGRADED <= error_rate < ERROR_RATE_THRESHOLD_UNHEALTHY, \
            f"Error rate {error_rate} should be between {ERROR_RATE_THRESHOLD_DEGRADED} and {ERROR_RATE_THRESHOLD_UNHEALTHY}"
        assert status == "degraded", f"Status should be 'degraded' but got '{status}' with error_rate={error_rate}"

        # Now add more errors to exceed UNHEALTHY threshold
        # We need total error_rate >= 0.6
        current_total = metrics.total_requests
        current_errors = len(metrics._error_timestamps)
        # (current_errors + additional) / (current_total + additional) >= 0.6
        # Let's add enough to push it over
        additional_errors = int(1.5 * current_total) + 1
        for _ in range(additional_errors):
            metrics.record_error(50.0, now)
        
        assert metrics.recent_error_rate >= ERROR_RATE_THRESHOLD_UNHEALTHY
        assert metrics.health_status == "unhealthy"

    def test_health_status_degraded_by_latency(self) -> None:
        """Test that health_status returns 'degraded' for high latency."""
        metrics = ProviderMetrics()

        # Create many base requests with low latency
        # We need enough so that when we add high latency, avg doesn't increase too much
        base_latency = 100.0
        base_count = 200  # Many base requests (more than rolling window size)
        for _ in range(base_count):
            metrics.record_success(base_latency)

        # Now avg_latency_ms should be around base_latency
        assert metrics.avg_latency_ms == pytest.approx(base_latency, rel=0.01)

        # Now add high latency requests - these will fill the rolling window
        # Since rolling window is limited to 100, it will contain only the last 100 requests
        # (all high latency), while avg includes all 200 base + 100 high = 300 requests
        high_latency = base_latency * LATENCY_THRESHOLD_FACTOR_DEGRADED * 3  # 600ms (3x threshold)
        for _ in range(100):  # Fill rolling window completely with high latency
            metrics.record_success(high_latency)

        # Rolling avg should be high (last 100 requests are all high latency)
        assert metrics.rolling_avg_latency_ms is not None
        assert metrics.rolling_avg_latency_ms == pytest.approx(high_latency, rel=0.01)
        
        # Avg should be lower (includes 200 base + 100 high = (200*100 + 100*600)/300 = 266.67)
        expected_avg = (base_count * base_latency + 100 * high_latency) / (base_count + 100)
        assert metrics.avg_latency_ms == pytest.approx(expected_avg, rel=0.01)
        
        # Rolling (600) should be > 2.0 * avg (266.67 * 2 = 533.33)
        assert metrics.rolling_avg_latency_ms > LATENCY_THRESHOLD_FACTOR_DEGRADED * metrics.avg_latency_ms
        assert metrics.health_status == "degraded"

    def test_health_status_healthy(self) -> None:
        """Test that health_status returns 'healthy' in normal conditions."""
        metrics = ProviderMetrics()

        # Create enough requests with normal latency and no errors
        for _ in range(MIN_REQUESTS_FOR_HEALTH):
            metrics.record_success(100.0)

        assert metrics.health_status == "healthy"

        # Add a few errors but below threshold
        now = datetime.now(timezone.utc)
        for _ in range(2):  # Less than threshold
            metrics.record_error(50.0, now)

        # Should still be healthy (error rate below threshold)
        assert metrics.health_status == "healthy"


class TestProviderMetricsTokenTracking:
    """Test token tracking and cost estimation in ProviderMetrics (v0.7.0)."""

    def test_initial_token_values(self) -> None:
        """Test that token fields initialize to 0."""
        metrics = ProviderMetrics()
        assert metrics.total_prompt_tokens == 0
        assert metrics.total_completion_tokens == 0
        assert metrics.total_tokens == 0  # computed property
        assert metrics.total_cost == 0.0

    def test_record_success_with_tokens(self) -> None:
        """Test record_success with token parameters."""
        metrics = ProviderMetrics()
        metrics.record_success(
            latency_ms=100.0,
            prompt_tokens=50,
            completion_tokens=30,
            cost=0.16,
        )

        assert metrics.total_prompt_tokens == 50
        assert metrics.total_completion_tokens == 30
        assert metrics.total_tokens == 80
        assert metrics.total_cost == pytest.approx(0.16)

    def test_record_success_backward_compatible(self) -> None:
        """Test that old code without tokens still works (backward compatibility)."""
        metrics = ProviderMetrics()
        metrics.record_success(100.0)  # Old signature (v0.6.0 style)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.total_prompt_tokens == 0  # Defaults to 0
        assert metrics.total_completion_tokens == 0
        assert metrics.total_tokens == 0
        assert metrics.total_cost == 0.0

    def test_multiple_requests_accumulate_tokens(self) -> None:
        """Test that multiple requests accumulate tokens correctly."""
        metrics = ProviderMetrics()

        metrics.record_success(100.0, prompt_tokens=10, completion_tokens=20, cost=0.05)
        metrics.record_success(150.0, prompt_tokens=15, completion_tokens=25, cost=0.08)

        assert metrics.total_prompt_tokens == 25
        assert metrics.total_completion_tokens == 45
        assert metrics.total_tokens == 70
        assert metrics.total_cost == pytest.approx(0.13)

    def test_record_error_does_not_affect_tokens(self) -> None:
        """Test that failed requests do not affect token counts."""
        metrics = ProviderMetrics()
        now = datetime.now(timezone.utc)

        # Successful request with tokens
        metrics.record_success(100.0, prompt_tokens=50, completion_tokens=30, cost=0.16)

        # Failed request (no tokens recorded)
        metrics.record_error(50.0, now)

        # Token counts should remain unchanged
        assert metrics.total_prompt_tokens == 50
        assert metrics.total_completion_tokens == 30
        assert metrics.total_tokens == 80
        assert metrics.total_cost == pytest.approx(0.16)

    def test_total_tokens_computed_property(self) -> None:
        """Test that total_tokens is correctly computed."""
        metrics = ProviderMetrics()

        # Add tokens in multiple requests
        metrics.record_success(100.0, prompt_tokens=100, completion_tokens=50)
        assert metrics.total_tokens == 150

        metrics.record_success(100.0, prompt_tokens=200, completion_tokens=100)
        assert metrics.total_tokens == 450  # 100 + 50 + 200 + 100

    def test_mixed_old_and_new_style_requests(self) -> None:
        """Test that old-style and new-style requests can be mixed."""
        metrics = ProviderMetrics()

        # Old-style request (no tokens)
        metrics.record_success(100.0)

        # New-style request (with tokens)
        metrics.record_success(150.0, prompt_tokens=50, completion_tokens=30, cost=0.16)

        # Another old-style request
        metrics.record_success(120.0)

        # Verify counts
        assert metrics.total_requests == 3
        assert metrics.successful_requests == 3
        assert metrics.total_prompt_tokens == 50
        assert metrics.total_completion_tokens == 30
        assert metrics.total_tokens == 80
        assert metrics.total_cost == pytest.approx(0.16)
