"""Tests for the rate limiter module."""

import time
from datetime import UTC, datetime, timedelta

import pytest

from monitor.rate_limiter import (
    BUDGET_ALLOCATION,
    RateLimitConfig,
    RateLimiter,
    RateLimitState,
    RequestBudget,
    create_rate_limiter,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_defaults(self) -> None:
        """Config has correct default values."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 5000
        assert config.requests_per_day == 50000
        assert config.warning_threshold == 0.80

    def test_custom_values(self) -> None:
        """Config accepts custom values."""
        config = RateLimitConfig(
            requests_per_minute=50,
            requests_per_hour=1000,
        )

        assert config.requests_per_minute == 50
        assert config.requests_per_hour == 1000


class TestRateLimitState:
    """Tests for RateLimitState."""

    def test_initial_state(self) -> None:
        """State initializes with None values."""
        state = RateLimitState()

        assert state.limit is None
        assert state.remaining is None
        assert state.reset_at is None

    def test_update_from_headers(self) -> None:
        """State updates from header values."""
        state = RateLimitState()
        state.update_from_headers(
            limit=100,
            remaining=50,
            reset_timestamp=1700000000.0,
        )

        assert state.limit == 100
        assert state.remaining == 50
        assert state.reset_at is not None
        assert state.last_updated is not None

    def test_partial_update(self) -> None:
        """State allows partial updates."""
        state = RateLimitState()
        state.update_from_headers(limit=100, remaining=None, reset_timestamp=None)

        assert state.limit == 100
        assert state.remaining is None


class TestBudgetAllocation:
    """Tests for budget allocation constants."""

    def test_allocations_sum_to_one(self) -> None:
        """Budget allocations should sum to 100%."""
        total = sum(BUDGET_ALLOCATION.values())
        assert abs(total - 1.0) < 0.001

    def test_all_budgets_have_allocation(self) -> None:
        """All budget types should have an allocation."""
        for budget in RequestBudget:
            assert budget in BUDGET_ALLOCATION


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_can_request_initially(self) -> None:
        """Fresh limiter allows requests."""
        limiter = RateLimiter()
        assert limiter.can_request()

    def test_can_request_tracks_minute_limit(self) -> None:
        """Limiter blocks when minute limit reached."""
        config = RateLimitConfig(requests_per_minute=3)
        limiter = RateLimiter(config=config)

        # Make requests up to limit
        for _ in range(3):
            assert limiter.can_request()
            limiter.record_request()

        # Next request should be blocked
        assert not limiter.can_request()

    def test_record_request_updates_all_windows(self) -> None:
        """Recording request updates all tracking windows."""
        limiter = RateLimiter()
        limiter.record_request()

        assert len(limiter.minute_requests) == 1
        assert len(limiter.hour_requests) == 1
        assert len(limiter.day_requests) == 1

    def test_record_request_tracks_budget(self) -> None:
        """Recording request tracks budget category."""
        limiter = RateLimiter()
        limiter.record_request(budget=RequestBudget.NEW_POSTS)
        limiter.record_request(budget=RequestBudget.NEW_POSTS)
        limiter.record_request(budget=RequestBudget.TRENDING)

        assert limiter.budget_usage[RequestBudget.NEW_POSTS] == 2
        assert limiter.budget_usage[RequestBudget.TRENDING] == 1

    def test_wait_time_zero_when_can_request(self) -> None:
        """Wait time is zero when requests are allowed."""
        limiter = RateLimiter()
        assert limiter.wait_time() == 0.0

    def test_wait_time_positive_when_limited(self) -> None:
        """Wait time is positive when rate limited."""
        config = RateLimitConfig(requests_per_minute=1, minute_window=60)
        limiter = RateLimiter(config=config)

        limiter.record_request()
        assert not limiter.can_request()

        wait = limiter.wait_time()
        assert wait > 0
        assert wait <= 60  # Should be within the minute window

    def test_update_from_response(self) -> None:
        """Limiter updates from API response headers."""
        limiter = RateLimiter()
        limiter.update_from_response(
            limit=100,
            remaining=42,
            reset_timestamp=time.time() + 60,
        )

        assert limiter.api_state.limit == 100
        assert limiter.api_state.remaining == 42

    def test_get_status(self) -> None:
        """Status returns comprehensive state."""
        limiter = RateLimiter()
        limiter.record_request(budget=RequestBudget.NEW_POSTS)

        status = limiter.get_status()

        assert "minute" in status
        assert "hour" in status
        assert "day" in status
        assert "api_reported" in status
        assert "budget_usage" in status
        assert "can_request" in status
        assert "wait_time_seconds" in status

        assert status["minute"]["used"] == 1
        assert status["minute"]["limit"] == 100
        assert status["minute"]["remaining"] == 99

    def test_reset_budget(self) -> None:
        """Reset budget clears per-minute usage."""
        limiter = RateLimiter()
        limiter.record_request(budget=RequestBudget.NEW_POSTS)
        limiter.record_request(budget=RequestBudget.TRENDING)

        limiter.reset_budget()

        for budget in RequestBudget:
            assert limiter.budget_usage[budget] == 0

    def test_check_thresholds_returns_warnings(self) -> None:
        """Check thresholds returns warnings when approaching limits."""
        config = RateLimitConfig(
            requests_per_minute=10,
            warning_threshold=0.80,
        )
        limiter = RateLimiter(config=config)

        # Make 8 requests (80% of limit)
        for _ in range(8):
            limiter.record_request()

        warnings = limiter.check_thresholds()
        assert len(warnings) >= 1
        assert "80%" in warnings[0] or "Minute" in warnings[0]

    def test_check_thresholds_empty_when_low(self) -> None:
        """No warnings when well below thresholds."""
        limiter = RateLimiter()

        # Make just a few requests
        for _ in range(5):
            limiter.record_request()

        warnings = limiter.check_thresholds()
        assert len(warnings) == 0


class TestRateLimiterConcurrency:
    """Tests for thread safety."""

    def test_concurrent_recording(self) -> None:
        """Limiter handles concurrent request recording."""
        import threading

        limiter = RateLimiter()
        threads = []

        def record_requests() -> None:
            for _ in range(10):
                limiter.record_request()

        # Start multiple threads
        for _ in range(5):
            t = threading.Thread(target=record_requests)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All 50 requests should be recorded
        status = limiter.get_status()
        assert status["minute"]["used"] == 50


class TestCreateRateLimiter:
    """Tests for create_rate_limiter factory function."""

    def test_default_values(self) -> None:
        """Factory creates limiter with default values."""
        limiter = create_rate_limiter()

        assert limiter.config.requests_per_minute == 100
        assert limiter.config.requests_per_hour == 5000
        assert limiter.config.requests_per_day == 50000

    def test_custom_values(self) -> None:
        """Factory accepts custom values."""
        limiter = create_rate_limiter(
            requests_per_minute=50,
            requests_per_hour=1000,
            requests_per_day=10000,
        )

        assert limiter.config.requests_per_minute == 50
        assert limiter.config.requests_per_hour == 1000
        assert limiter.config.requests_per_day == 10000
