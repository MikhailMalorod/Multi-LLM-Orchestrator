"""Metrics module for tracking provider performance and health status.

This module provides ProviderMetrics class for collecting and analyzing
performance metrics of LLM providers, including request counts, latency,
error rates, and health status determination.
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Literal

# ============================================================================
# CONSTANTS
# ============================================================================

# Size of rolling window for latency tracking
LATENCY_WINDOW_SIZE = 100

# Time window for error tracking (in seconds)
ERROR_WINDOW_SECONDS = 60

# Minimum requests required to assess health status
MIN_REQUESTS_FOR_HEALTH = 5

# Minimum requests required for latency comparison
MIN_REQUESTS_FOR_LATENCY_CHECK = 20

# Error rate threshold for degraded status (30%)
ERROR_RATE_THRESHOLD_DEGRADED = 0.3

# Error rate threshold for unhealthy status (60%)
ERROR_RATE_THRESHOLD_UNHEALTHY = 0.6

# Latency multiplier threshold for degraded status (2x average)
LATENCY_THRESHOLD_FACTOR_DEGRADED = 2.0

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

HealthStatus = Literal["healthy", "degraded", "unhealthy"]

# ============================================================================
# PROVIDER METRICS
# ============================================================================


class ProviderMetrics:
    """Metrics tracker for LLM provider performance and health.

    This class collects and analyzes metrics for a single provider instance,
    including request counts, latency measurements, error rates, and health
    status determination based on configurable thresholds.

    Attributes:
        total_requests: Total number of requests made to the provider
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        total_latency_ms: Sum of latency for successful requests only (in milliseconds)

    Example:
        ```python
        from orchestrator.metrics import ProviderMetrics
        from datetime import UTC, datetime

        metrics = ProviderMetrics()
        metrics.record_success(150.5)  # Successful request with 150.5ms latency
        metrics.record_error(50.0, datetime.now(UTC))  # Failed request

        print(metrics.success_rate)  # 0.5
        print(metrics.avg_latency_ms)  # 150.5
        print(metrics.health_status)  # "healthy" or "degraded" or "unhealthy"
        ```
    """

    def __init__(self) -> None:
        """Initialize ProviderMetrics with zero counters and empty collections."""
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.total_latency_ms: float = 0.0

        # Rolling window for latency (automatically limited to LATENCY_WINDOW_SIZE)
        self._latency_window: deque[float] = deque(maxlen=LATENCY_WINDOW_SIZE)

        # Error timestamps (manually cleaned up in record_error)
        self._error_timestamps: deque[datetime] = deque()

        # Token tracking and cost estimation (v0.7.0)
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost: float = 0.0

    def record_success(
        self,
        latency_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record a successful request with latency, tokens, and cost.

        This method updates counters and adds the latency measurement to
        the rolling window. Only successful requests contribute to
        total_latency_ms for average latency calculation.

        Args:
            latency_ms: Request latency in milliseconds
            prompt_tokens: Number of tokens in prompt (default: 0, v0.7.0+)
            completion_tokens: Number of tokens in completion (default: 0, v0.7.0+)
            cost: Request cost in RUB (default: 0.0, v0.7.0+)

        Example:
            ```python
            # Backward compatible (v0.6.0 style)
            metrics.record_success(125.3)

            # With token tracking (v0.7.0+)
            metrics.record_success(
                latency_ms=125.3,
                prompt_tokens=50,
                completion_tokens=30,
                cost=0.16
            )
            ```
        """
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency_ms += latency_ms
        self._latency_window.append(latency_ms)

        # Update token and cost tracking (v0.7.0+)
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost += cost

    def record_error(
        self, latency_ms: float, error_timestamp: datetime
    ) -> None:
        """Record a failed request with its latency and timestamp.

        This method updates counters and adds the error timestamp to the
        error tracking window. Old error timestamps (beyond ERROR_WINDOW_SECONDS)
        are automatically cleaned up.

        Args:
            latency_ms: Request latency in milliseconds (even for failed requests)
            error_timestamp: Timestamp when the error occurred (should be timezone-aware)

        Example:
            ```python
            from datetime import UTC, datetime

            metrics.record_error(50.0, datetime.now(UTC))
            ```
        """
        self.total_requests += 1
        self.failed_requests += 1
        # Note: total_latency_ms is NOT updated here - avg_latency_ms
        # is calculated only from successful requests
        self._error_timestamps.append(error_timestamp)

        # Clean up old error timestamps (beyond ERROR_WINDOW_SECONDS)
        cutoff = error_timestamp - timedelta(seconds=ERROR_WINDOW_SECONDS)
        while self._error_timestamps and self._error_timestamps[0] < cutoff:
            self._error_timestamps.popleft()

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a ratio of successful to total requests.

        Returns:
            Success rate between 0.0 and 1.0. Returns 0.0 if no requests made.

        Example:
            ```python
            metrics.record_success(100.0)
            metrics.record_error(50.0, datetime.now(UTC))
            print(metrics.success_rate)  # 0.5
            ```
        """
        return self.successful_requests / max(1, self.total_requests)

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency for successful requests only.

        Returns:
            Average latency in milliseconds. Returns 0.0 if no successful requests.

        Example:
            ```python
            metrics.record_success(100.0)
            metrics.record_success(200.0)
            print(metrics.avg_latency_ms)  # 150.0
            ```
        """
        return self.total_latency_ms / max(1, self.successful_requests)

    @property
    def rolling_avg_latency_ms(self) -> float | None:
        """Calculate rolling average latency from the sliding window.

        Returns:
            Rolling average latency in milliseconds, or None if window is empty.

        Example:
            ```python
            for i in range(10):
                metrics.record_success(100.0 + i)
            print(metrics.rolling_avg_latency_ms)  # ~104.5 (average of last 10)
            ```
        """
        if len(self._latency_window) == 0:
            return None
        return sum(self._latency_window) / len(self._latency_window)

    @property
    def total_tokens(self) -> int:
        """Calculate total tokens processed (prompt + completion).

        Returns:
            Sum of prompt and completion tokens

        Example:
            ```python
            metrics.record_success(100.0, prompt_tokens=50, completion_tokens=30)
            print(metrics.total_tokens)  # 80
            ```
        """
        return self.total_prompt_tokens + self.total_completion_tokens

    @property
    def recent_error_rate(self) -> float:
        """Calculate recent error rate (simplified formula).

        Uses simplified formula: number of errors in tracking window
        divided by total requests. This provides a simple approximation
        of error rate without tracking "requests in last 60 seconds" separately.

        Returns:
            Error rate between 0.0 and 1.0. Returns 0.0 if no requests made.

        Example:
            ```python
            # If 3 errors out of 10 total requests
            print(metrics.recent_error_rate)  # 0.3
            ```
        """
        return len(self._error_timestamps) / max(1, self.total_requests)

    @property
    def health_status(self) -> HealthStatus:
        """Determine provider health status based on metrics.

        Health status is determined using the following logic:
        1. If insufficient data (total_requests < MIN_REQUESTS_FOR_HEALTH):
           → "healthy" (optimistic default)
        2. If recent_error_rate >= ERROR_RATE_THRESHOLD_UNHEALTHY (0.6):
           → "unhealthy"
        3. If recent_error_rate >= ERROR_RATE_THRESHOLD_DEGRADED (0.3):
           → "degraded"
        4. If rolling_avg_latency_ms > 2.0 * avg_latency_ms (and enough data):
           → "degraded"
        5. Otherwise:
           → "healthy"

        Returns:
            Health status: "healthy", "degraded", or "unhealthy"

        Example:
            ```python
            # With many errors
            for _ in range(10):
                metrics.record_error(50.0, datetime.now(UTC))
            print(metrics.health_status)  # "unhealthy"

            # With normal operation
            for _ in range(10):
                metrics.record_success(100.0)
            print(metrics.health_status)  # "healthy"
            ```
        """
        # If insufficient data, return "healthy" (optimistic default)
        if self.total_requests < MIN_REQUESTS_FOR_HEALTH:
            return "healthy"

        # Check error rate thresholds
        error_rate = self.recent_error_rate
        if error_rate >= ERROR_RATE_THRESHOLD_UNHEALTHY:
            return "unhealthy"
        if error_rate >= ERROR_RATE_THRESHOLD_DEGRADED:
            return "degraded"

        # Check latency degradation (only if enough data)
        if self.total_requests >= MIN_REQUESTS_FOR_LATENCY_CHECK:
            rolling_avg = self.rolling_avg_latency_ms
            avg_latency = self.avg_latency_ms

            if (
                rolling_avg is not None
                and avg_latency > 0
                and rolling_avg
                > LATENCY_THRESHOLD_FACTOR_DEGRADED * avg_latency
            ):
                return "degraded"

        # Default to healthy
        return "healthy"

