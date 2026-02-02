"""Rate limiter for Moltbook API requests.

Implements a sliding window rate limiter that tracks:
- Requests per minute (primary limit: 100/min)
- Requests per hour (secondary limit: 5,000/hr)
- Requests per day (tertiary limit: 50,000/day)

Also tracks rate limit headers from API responses and warns
when approaching thresholds (80%).

Budget allocation:
- 40% new posts
- 20% trending
- 20% comments
- 10% agents
- 10% reserve
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from threading import RLock
from typing import Any

logger = logging.getLogger(__name__)


class RequestBudget(str, Enum):
    """Request budget categories for rate limiting."""

    NEW_POSTS = "new_posts"
    TRENDING = "trending"
    COMMENTS = "comments"
    AGENTS = "agents"
    RESERVE = "reserve"


# Budget allocation percentages (must sum to 100)
BUDGET_ALLOCATION: dict[RequestBudget, float] = {
    RequestBudget.NEW_POSTS: 0.40,
    RequestBudget.TRENDING: 0.20,
    RequestBudget.COMMENTS: 0.20,
    RequestBudget.AGENTS: 0.10,
    RequestBudget.RESERVE: 0.10,
}


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    # Primary limits
    requests_per_minute: int = 100
    requests_per_hour: int = 5000
    requests_per_day: int = 50000

    # Warning thresholds (percentage of limit)
    warning_threshold: float = 0.80

    # Window sizes for sliding window
    minute_window: int = 60  # seconds
    hour_window: int = 3600  # seconds
    day_window: int = 86400  # seconds


@dataclass
class RateLimitState:
    """Current state of rate limits from API headers."""

    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None
    last_updated: datetime | None = None

    def update_from_headers(
        self,
        limit: int | None,
        remaining: int | None,
        reset_timestamp: float | None,
    ) -> None:
        """Update state from API response headers."""
        if limit is not None:
            self.limit = limit
        if remaining is not None:
            self.remaining = remaining
        if reset_timestamp is not None:
            self.reset_at = datetime.fromtimestamp(reset_timestamp, tz=UTC)
        self.last_updated = datetime.now(UTC)


@dataclass
class RateLimiter:
    """Sliding window rate limiter for API requests.

    Tracks requests across minute, hour, and day windows.
    Provides methods to check if a request can be made and
    calculate wait times when rate limited.

    Attributes:
        config: Rate limit configuration
        minute_requests: Deque of timestamps for minute window
        hour_requests: Deque of timestamps for hour window
        day_requests: Deque of timestamps for day window
        api_state: Rate limit state from API headers
        budget_usage: Per-category request counts
    """

    config: RateLimitConfig = field(default_factory=RateLimitConfig)
    minute_requests: deque[float] = field(default_factory=deque)
    hour_requests: deque[float] = field(default_factory=deque)
    day_requests: deque[float] = field(default_factory=deque)
    api_state: RateLimitState = field(default_factory=RateLimitState)
    budget_usage: dict[RequestBudget, int] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def __post_init__(self) -> None:
        """Initialize budget usage tracking."""
        for budget in RequestBudget:
            self.budget_usage.setdefault(budget, 0)

    def _cleanup_old_requests(self, now: float) -> None:
        """Remove requests outside the tracking windows."""
        minute_cutoff = now - self.config.minute_window
        hour_cutoff = now - self.config.hour_window
        day_cutoff = now - self.config.day_window

        while self.minute_requests and self.minute_requests[0] < minute_cutoff:
            self.minute_requests.popleft()

        while self.hour_requests and self.hour_requests[0] < hour_cutoff:
            self.hour_requests.popleft()

        while self.day_requests and self.day_requests[0] < day_cutoff:
            self.day_requests.popleft()

    def _get_counts(self, now: float) -> tuple[int, int, int]:
        """Get current request counts for each window."""
        self._cleanup_old_requests(now)
        return (
            len(self.minute_requests),
            len(self.hour_requests),
            len(self.day_requests),
        )

    def can_request(self, budget: RequestBudget | None = None) -> bool:
        """Check if a request can be made without exceeding limits.

        Args:
            budget: Optional budget category to check against allocation

        Returns:
            True if request is allowed, False otherwise
        """
        with self._lock:
            now = time.time()
            minute_count, hour_count, day_count = self._get_counts(now)

            # Check hard limits
            if minute_count >= self.config.requests_per_minute:
                return False
            if hour_count >= self.config.requests_per_hour:
                return False
            if day_count >= self.config.requests_per_day:
                return False

            # Check API-reported remaining (if available)
            if (
                self.api_state.remaining is not None
                and self.api_state.remaining <= 0
                and self.api_state.reset_at
                and datetime.now(UTC) < self.api_state.reset_at
            ):
                return False

            # Check budget allocation if specified
            if budget is not None:
                allocation = BUDGET_ALLOCATION.get(budget, 0.0)
                max_for_budget = int(self.config.requests_per_minute * allocation)
                if self.budget_usage.get(budget, 0) >= max_for_budget:
                    # Budget exhausted, but allow if reserve available
                    reserve_remaining = int(
                        self.config.requests_per_minute
                        * BUDGET_ALLOCATION[RequestBudget.RESERVE]
                    ) - self.budget_usage.get(RequestBudget.RESERVE, 0)
                    if reserve_remaining <= 0:
                        return False

            return True

    def record_request(self, budget: RequestBudget = RequestBudget.RESERVE) -> None:
        """Record that a request was made.

        Args:
            budget: Budget category this request belongs to
        """
        with self._lock:
            now = time.time()
            self.minute_requests.append(now)
            self.hour_requests.append(now)
            self.day_requests.append(now)
            self.budget_usage[budget] = self.budget_usage.get(budget, 0) + 1

    def update_from_response(
        self,
        limit: int | None = None,
        remaining: int | None = None,
        reset_timestamp: float | None = None,
    ) -> None:
        """Update rate limit state from API response headers.

        Args:
            limit: X-RateLimit-Limit header value
            remaining: X-RateLimit-Remaining header value
            reset_timestamp: X-RateLimit-Reset header value (Unix timestamp)
        """
        with self._lock:
            self.api_state.update_from_headers(limit, remaining, reset_timestamp)

            # Log warnings if approaching limits
            if remaining is not None and limit is not None:
                used_pct = 1.0 - (remaining / limit)
                if used_pct >= self.config.warning_threshold:
                    logger.warning(
                        "Approaching rate limit: %d/%d remaining (%.0f%% used)",
                        remaining,
                        limit,
                        used_pct * 100,
                    )

    def wait_time(self) -> float:
        """Calculate time to wait before next request is allowed.

        Returns:
            Seconds to wait (0.0 if request can be made immediately)
        """
        with self._lock:
            now = time.time()
            minute_count, hour_count, day_count = self._get_counts(now)

            # Check minute limit
            if minute_count >= self.config.requests_per_minute:
                # Wait until oldest request exits the minute window
                oldest = self.minute_requests[0] if self.minute_requests else now
                wait = (oldest + self.config.minute_window) - now
                if wait > 0:
                    return wait

            # Check hour limit
            if hour_count >= self.config.requests_per_hour:
                oldest = self.hour_requests[0] if self.hour_requests else now
                wait = (oldest + self.config.hour_window) - now
                if wait > 0:
                    return wait

            # Check day limit
            if day_count >= self.config.requests_per_day:
                oldest = self.day_requests[0] if self.day_requests else now
                wait = (oldest + self.config.day_window) - now
                if wait > 0:
                    return wait

            # Check API-reported reset time
            if (
                self.api_state.remaining is not None
                and self.api_state.remaining <= 0
                and self.api_state.reset_at
            ):
                reset_wait = (
                    self.api_state.reset_at - datetime.now(UTC)
                ).total_seconds()
                if reset_wait > 0:
                    return reset_wait

            return 0.0

    def get_status(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
            Dict with current counts, limits, and usage
        """
        with self._lock:
            now = time.time()
            minute_count, hour_count, day_count = self._get_counts(now)

            return {
                "minute": {
                    "used": minute_count,
                    "limit": self.config.requests_per_minute,
                    "remaining": self.config.requests_per_minute - minute_count,
                },
                "hour": {
                    "used": hour_count,
                    "limit": self.config.requests_per_hour,
                    "remaining": self.config.requests_per_hour - hour_count,
                },
                "day": {
                    "used": day_count,
                    "limit": self.config.requests_per_day,
                    "remaining": self.config.requests_per_day - day_count,
                },
                "api_reported": {
                    "limit": self.api_state.limit,
                    "remaining": self.api_state.remaining,
                    "reset_at": (
                        self.api_state.reset_at.isoformat()
                        if self.api_state.reset_at
                        else None
                    ),
                },
                "budget_usage": dict(self.budget_usage),
                "can_request": self.can_request(),
                "wait_time_seconds": self.wait_time(),
            }

    def reset_budget(self) -> None:
        """Reset per-minute budget usage counters.

        Should be called at the start of each minute.
        """
        with self._lock:
            for budget in RequestBudget:
                self.budget_usage[budget] = 0

    def check_thresholds(self) -> list[str]:
        """Check if any rate limits are approaching thresholds.

        Returns:
            List of warning messages for limits approaching threshold
        """
        warnings: list[str] = []
        with self._lock:
            now = time.time()
            minute_count, hour_count, day_count = self._get_counts(now)

            # Check each limit against threshold
            minute_pct = minute_count / self.config.requests_per_minute
            if minute_pct >= self.config.warning_threshold:
                warnings.append(
                    f"Minute limit at {minute_pct:.0%} "
                    f"({minute_count}/{self.config.requests_per_minute})"
                )

            hour_pct = hour_count / self.config.requests_per_hour
            if hour_pct >= self.config.warning_threshold:
                warnings.append(
                    f"Hour limit at {hour_pct:.0%} "
                    f"({hour_count}/{self.config.requests_per_hour})"
                )

            day_pct = day_count / self.config.requests_per_day
            if day_pct >= self.config.warning_threshold:
                warnings.append(
                    f"Day limit at {day_pct:.0%} "
                    f"({day_count}/{self.config.requests_per_day})"
                )

        return warnings


def create_rate_limiter(
    requests_per_minute: int = 100,
    requests_per_hour: int = 5000,
    requests_per_day: int = 50000,
) -> RateLimiter:
    """Create a rate limiter with the specified limits.

    Args:
        requests_per_minute: Max requests per minute (default: 100)
        requests_per_hour: Max requests per hour (default: 5000)
        requests_per_day: Max requests per day (default: 50000)

    Returns:
        Configured RateLimiter instance
    """
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        requests_per_day=requests_per_day,
    )
    return RateLimiter(config=config)
