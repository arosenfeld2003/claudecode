"""Error handling and backoff strategies for API requests.

Implements exponential backoff with jitter for handling:
- 429 Rate Limited responses (respect Retry-After header)
- 500-599 Server errors (exponential backoff)
- 400-499 Client errors (log and skip, no retry)
- Timeout errors (linear backoff)

Backoff formula: delay = base * 2^min(error_count, max_exponent) * jitter
Jitter range: 0.8 to 1.2
Maximum delay: 5 minutes (300 seconds)
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors for backoff handling."""

    RATE_LIMITED = "rate_limited"  # 429
    SERVER_ERROR = "server_error"  # 500-599
    CLIENT_ERROR = "client_error"  # 400-499 (except 429)
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    UNKNOWN = "unknown"


@dataclass
class BackoffConfig:
    """Configuration for backoff behavior."""

    # Base delay in seconds
    base_delay: float = 1.0

    # Maximum exponent for exponential backoff
    max_exponent: int = 8

    # Maximum delay in seconds (5 minutes)
    max_delay: float = 300.0

    # Jitter range (multiplier applied to delay)
    jitter_min: float = 0.8
    jitter_max: float = 1.2

    # Linear backoff multiplier for timeouts
    timeout_multiplier: float = 2.0


@dataclass
class BackoffState:
    """Current backoff state for an endpoint or operation."""

    error_count: int = 0
    last_error_at: datetime | None = None
    last_error_type: ErrorType | None = None
    retry_after: datetime | None = None
    consecutive_successes: int = 0

    def record_error(self, error_type: ErrorType, retry_after_seconds: float | None = None) -> None:
        """Record an error occurrence."""
        self.error_count += 1
        self.last_error_at = datetime.now(UTC)
        self.last_error_type = error_type
        self.consecutive_successes = 0

        if retry_after_seconds is not None:
            self.retry_after = datetime.now(UTC) + timedelta(seconds=retry_after_seconds)
        else:
            self.retry_after = None

    def record_success(self) -> None:
        """Record a successful request."""
        self.consecutive_successes += 1
        # Reset error count after 3 consecutive successes
        if self.consecutive_successes >= 3:
            self.error_count = 0
            self.last_error_type = None
            self.retry_after = None

    def reset(self) -> None:
        """Reset all backoff state."""
        self.error_count = 0
        self.last_error_at = None
        self.last_error_type = None
        self.retry_after = None
        self.consecutive_successes = 0


@dataclass
class BackoffHandler:
    """Handles error backoff calculations and state management.

    Provides:
    - Exponential backoff for rate limits and server errors
    - Linear backoff for timeouts
    - Retry-After header respect for 429 responses
    - Per-endpoint state tracking
    """

    config: BackoffConfig = field(default_factory=BackoffConfig)
    endpoint_states: dict[str, BackoffState] = field(default_factory=dict)

    def _get_state(self, endpoint: str) -> BackoffState:
        """Get or create state for an endpoint."""
        if endpoint not in self.endpoint_states:
            self.endpoint_states[endpoint] = BackoffState()
        return self.endpoint_states[endpoint]

    def _apply_jitter(self, delay: float) -> float:
        """Apply jitter to a delay value."""
        jitter = random.uniform(self.config.jitter_min, self.config.jitter_max)
        return delay * jitter

    def calculate_delay(
        self,
        endpoint: str,
        error_type: ErrorType,
        retry_after_seconds: float | None = None,
    ) -> float:
        """Calculate delay before next retry.

        Args:
            endpoint: The endpoint that failed
            error_type: Type of error encountered
            retry_after_seconds: Retry-After header value if present

        Returns:
            Delay in seconds before next request should be attempted
        """
        state = self._get_state(endpoint)

        # Client errors should not be retried
        if error_type == ErrorType.CLIENT_ERROR:
            return 0.0

        # If Retry-After header is present, use it
        if retry_after_seconds is not None and retry_after_seconds > 0:
            return min(retry_after_seconds, self.config.max_delay)

        # Calculate base delay based on error type
        if error_type == ErrorType.TIMEOUT:
            # Linear backoff for timeouts
            delay = self.config.base_delay * self.config.timeout_multiplier * state.error_count
        else:
            # Exponential backoff for rate limits and server errors
            exponent = min(state.error_count, self.config.max_exponent)
            delay = self.config.base_delay * (2 ** exponent)

        # Apply jitter and cap at max delay
        delay = self._apply_jitter(delay)
        return min(delay, self.config.max_delay)

    def record_error(
        self,
        endpoint: str,
        error_type: ErrorType,
        retry_after_seconds: float | None = None,
    ) -> float:
        """Record an error and return the calculated delay.

        Args:
            endpoint: The endpoint that failed
            error_type: Type of error encountered
            retry_after_seconds: Retry-After header value if present

        Returns:
            Delay in seconds before next request should be attempted
        """
        state = self._get_state(endpoint)
        state.record_error(error_type, retry_after_seconds)

        delay = self.calculate_delay(endpoint, error_type, retry_after_seconds)

        logger.info(
            "Backoff for %s: error_type=%s, error_count=%d, delay=%.2fs",
            endpoint,
            error_type.value,
            state.error_count,
            delay,
        )

        return delay

    def record_success(self, endpoint: str) -> None:
        """Record a successful request for an endpoint.

        Args:
            endpoint: The endpoint that succeeded
        """
        state = self._get_state(endpoint)
        state.record_success()

    def should_retry(self, endpoint: str, error_type: ErrorType) -> bool:
        """Determine if a request should be retried.

        Args:
            endpoint: The endpoint that failed
            error_type: Type of error encountered

        Returns:
            True if the request should be retried, False otherwise
        """
        # Never retry client errors (400-499 except 429)
        if error_type == ErrorType.CLIENT_ERROR:
            return False

        state = self._get_state(endpoint)

        # Don't retry if we've hit max error count
        if state.error_count >= self.config.max_exponent:
            logger.warning(
                "Max retries reached for %s (error_count=%d)",
                endpoint,
                state.error_count,
            )
            return False

        return True

    def get_next_allowed_time(self, endpoint: str) -> datetime | None:
        """Get the next time a request is allowed for an endpoint.

        Args:
            endpoint: The endpoint to check

        Returns:
            Datetime when next request is allowed, or None if allowed now
        """
        state = self._get_state(endpoint)

        if state.retry_after is not None and datetime.now(UTC) < state.retry_after:
            return state.retry_after

        if state.last_error_at is None:
            return None

        # Calculate when backoff expires
        delay = self.calculate_delay(
            endpoint,
            state.last_error_type or ErrorType.UNKNOWN,
        )
        next_allowed = state.last_error_at + timedelta(seconds=delay)

        if datetime.now(UTC) < next_allowed:
            return next_allowed

        return None

    def reset_endpoint(self, endpoint: str) -> None:
        """Reset backoff state for an endpoint.

        Args:
            endpoint: The endpoint to reset
        """
        if endpoint in self.endpoint_states:
            self.endpoint_states[endpoint].reset()

    def reset_all(self) -> None:
        """Reset backoff state for all endpoints."""
        self.endpoint_states.clear()

    def get_status(self) -> dict[str, Any]:
        """Get current backoff status for all endpoints.

        Returns:
            Dict with endpoint states and config
        """
        return {
            "config": {
                "base_delay": self.config.base_delay,
                "max_delay": self.config.max_delay,
                "max_exponent": self.config.max_exponent,
            },
            "endpoints": {
                endpoint: {
                    "error_count": state.error_count,
                    "last_error_at": (
                        state.last_error_at.isoformat()
                        if state.last_error_at
                        else None
                    ),
                    "last_error_type": (
                        state.last_error_type.value if state.last_error_type else None
                    ),
                    "retry_after": (
                        state.retry_after.isoformat() if state.retry_after else None
                    ),
                    "consecutive_successes": state.consecutive_successes,
                }
                for endpoint, state in self.endpoint_states.items()
            },
        }


def classify_http_error(status_code: int) -> ErrorType:
    """Classify an HTTP status code into an error type.

    Args:
        status_code: HTTP status code

    Returns:
        ErrorType for the status code
    """
    if status_code == 429:
        return ErrorType.RATE_LIMITED
    elif 400 <= status_code < 500:
        return ErrorType.CLIENT_ERROR
    elif 500 <= status_code < 600:
        return ErrorType.SERVER_ERROR
    else:
        return ErrorType.UNKNOWN


def parse_retry_after(header_value: str | None) -> float | None:
    """Parse Retry-After header value.

    The header can be either:
    - A number of seconds (e.g., "120")
    - An HTTP-date (e.g., "Wed, 21 Oct 2015 07:28:00 GMT")

    Args:
        header_value: The Retry-After header value

    Returns:
        Seconds to wait, or None if header is missing/invalid
    """
    if header_value is None:
        return None

    # Try parsing as seconds
    try:
        return float(header_value)
    except ValueError:
        pass

    # Try parsing as HTTP-date
    try:
        from email.utils import parsedate_to_datetime

        retry_datetime = parsedate_to_datetime(header_value)
        delta = retry_datetime - datetime.now(UTC)
        return max(0.0, delta.total_seconds())
    except (ValueError, TypeError):
        pass

    return None


def create_backoff_handler(
    base_delay: float = 1.0,
    max_delay: float = 300.0,
) -> BackoffHandler:
    """Create a backoff handler with the specified config.

    Args:
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 300.0 = 5 minutes)

    Returns:
        Configured BackoffHandler instance
    """
    config = BackoffConfig(base_delay=base_delay, max_delay=max_delay)
    return BackoffHandler(config=config)
