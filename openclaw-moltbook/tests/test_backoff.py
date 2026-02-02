"""Tests for the backoff module."""

from datetime import UTC, datetime, timedelta

import pytest

from monitor.backoff import (
    BackoffConfig,
    BackoffHandler,
    BackoffState,
    ErrorType,
    classify_http_error,
    create_backoff_handler,
    parse_retry_after,
)


class TestErrorType:
    """Tests for error classification."""

    def test_classify_rate_limited(self) -> None:
        """429 is classified as rate limited."""
        assert classify_http_error(429) == ErrorType.RATE_LIMITED

    def test_classify_client_errors(self) -> None:
        """400-499 (except 429) are client errors."""
        assert classify_http_error(400) == ErrorType.CLIENT_ERROR
        assert classify_http_error(404) == ErrorType.CLIENT_ERROR
        assert classify_http_error(403) == ErrorType.CLIENT_ERROR

    def test_classify_server_errors(self) -> None:
        """500-599 are server errors."""
        assert classify_http_error(500) == ErrorType.SERVER_ERROR
        assert classify_http_error(502) == ErrorType.SERVER_ERROR
        assert classify_http_error(503) == ErrorType.SERVER_ERROR

    def test_classify_unknown(self) -> None:
        """Other status codes are unknown."""
        assert classify_http_error(200) == ErrorType.UNKNOWN
        assert classify_http_error(301) == ErrorType.UNKNOWN


class TestParseRetryAfter:
    """Tests for Retry-After header parsing."""

    def test_parse_seconds(self) -> None:
        """Parse numeric seconds value."""
        assert parse_retry_after("120") == 120.0
        assert parse_retry_after("60") == 60.0
        assert parse_retry_after("0") == 0.0

    def test_parse_none(self) -> None:
        """Return None for missing header."""
        assert parse_retry_after(None) is None

    def test_parse_invalid(self) -> None:
        """Return None for invalid values."""
        assert parse_retry_after("invalid") is None
        assert parse_retry_after("") is None


class TestBackoffConfig:
    """Tests for BackoffConfig."""

    def test_defaults(self) -> None:
        """Config has correct defaults."""
        config = BackoffConfig()

        assert config.base_delay == 1.0
        assert config.max_exponent == 8
        assert config.max_delay == 300.0
        assert config.jitter_min == 0.8
        assert config.jitter_max == 1.2

    def test_custom_values(self) -> None:
        """Config accepts custom values."""
        config = BackoffConfig(
            base_delay=2.0,
            max_delay=60.0,
        )

        assert config.base_delay == 2.0
        assert config.max_delay == 60.0


class TestBackoffState:
    """Tests for BackoffState."""

    def test_initial_state(self) -> None:
        """State initializes with zero errors."""
        state = BackoffState()

        assert state.error_count == 0
        assert state.last_error_at is None
        assert state.retry_after is None
        assert state.consecutive_successes == 0

    def test_record_error(self) -> None:
        """Recording error updates state."""
        state = BackoffState()
        state.record_error(ErrorType.SERVER_ERROR)

        assert state.error_count == 1
        assert state.last_error_at is not None
        assert state.last_error_type == ErrorType.SERVER_ERROR
        assert state.consecutive_successes == 0

    def test_record_error_with_retry_after(self) -> None:
        """Recording error with retry-after sets retry time."""
        state = BackoffState()
        state.record_error(ErrorType.RATE_LIMITED, retry_after_seconds=60.0)

        assert state.retry_after is not None
        # Should be about 60 seconds from now
        delta = state.retry_after - datetime.now(UTC)
        assert 59 <= delta.total_seconds() <= 61

    def test_record_success(self) -> None:
        """Recording success increments consecutive count."""
        state = BackoffState()
        state.record_error(ErrorType.SERVER_ERROR)
        state.record_success()

        assert state.consecutive_successes == 1
        assert state.error_count == 1  # Not reset yet

    def test_record_success_resets_after_three(self) -> None:
        """Three consecutive successes resets error count."""
        state = BackoffState()
        state.record_error(ErrorType.SERVER_ERROR)
        state.record_error(ErrorType.SERVER_ERROR)

        state.record_success()
        state.record_success()
        state.record_success()

        assert state.error_count == 0
        assert state.last_error_type is None

    def test_reset(self) -> None:
        """Reset clears all state."""
        state = BackoffState()
        state.record_error(ErrorType.SERVER_ERROR)
        state.record_success()
        state.reset()

        assert state.error_count == 0
        assert state.last_error_at is None
        assert state.consecutive_successes == 0


class TestBackoffHandler:
    """Tests for BackoffHandler."""

    def test_calculate_delay_client_error(self) -> None:
        """Client errors have zero delay (no retry)."""
        handler = BackoffHandler()
        delay = handler.calculate_delay("test", ErrorType.CLIENT_ERROR)

        assert delay == 0.0

    def test_calculate_delay_exponential(self) -> None:
        """Server errors use exponential backoff."""
        handler = BackoffHandler()

        # First error: base_delay * 2^1 = 2.0 (with jitter 0.8-1.2 = 1.6-2.4)
        handler.record_error("test", ErrorType.SERVER_ERROR)
        delay1 = handler.calculate_delay("test", ErrorType.SERVER_ERROR)

        # Second error: base_delay * 2^2 = 4.0 (with jitter 0.8-1.2 = 3.2-4.8)
        handler.record_error("test", ErrorType.SERVER_ERROR)
        delay2 = handler.calculate_delay("test", ErrorType.SERVER_ERROR)

        # Third error: base_delay * 2^3 = 8.0 (with jitter 0.8-1.2 = 6.4-9.6)
        handler.record_error("test", ErrorType.SERVER_ERROR)
        delay3 = handler.calculate_delay("test", ErrorType.SERVER_ERROR)

        # Delays should increase (third should always be > first given jitter range)
        # delay1 max = 2.4, delay3 min = 6.4, so delay3 > delay1 always
        assert delay3 > delay1

    def test_calculate_delay_respects_max(self) -> None:
        """Delay is capped at max_delay."""
        config = BackoffConfig(max_delay=10.0)
        handler = BackoffHandler(config=config)

        # Record many errors
        for _ in range(20):
            handler.record_error("test", ErrorType.SERVER_ERROR)

        delay = handler.calculate_delay("test", ErrorType.SERVER_ERROR)
        assert delay <= 10.0

    def test_calculate_delay_uses_retry_after(self) -> None:
        """Retry-After header is respected."""
        handler = BackoffHandler()
        delay = handler.calculate_delay(
            "test", ErrorType.RATE_LIMITED, retry_after_seconds=30.0
        )

        assert delay == 30.0

    def test_record_error_returns_delay(self) -> None:
        """record_error returns the calculated delay."""
        handler = BackoffHandler()
        delay = handler.record_error("test", ErrorType.SERVER_ERROR)

        assert delay > 0

    def test_record_success(self) -> None:
        """Recording success updates state."""
        handler = BackoffHandler()
        handler.record_error("test", ErrorType.SERVER_ERROR)
        handler.record_success("test")

        state = handler.endpoint_states["test"]
        assert state.consecutive_successes == 1

    def test_should_retry_server_error(self) -> None:
        """Server errors should be retried."""
        handler = BackoffHandler()
        assert handler.should_retry("test", ErrorType.SERVER_ERROR)

    def test_should_retry_client_error(self) -> None:
        """Client errors should not be retried."""
        handler = BackoffHandler()
        assert not handler.should_retry("test", ErrorType.CLIENT_ERROR)

    def test_should_retry_max_reached(self) -> None:
        """Should not retry after max errors."""
        config = BackoffConfig(max_exponent=3)
        handler = BackoffHandler(config=config)

        # Record max errors
        for _ in range(3):
            handler.record_error("test", ErrorType.SERVER_ERROR)

        assert not handler.should_retry("test", ErrorType.SERVER_ERROR)

    def test_get_next_allowed_time(self) -> None:
        """Get next allowed time for endpoint."""
        handler = BackoffHandler()

        # No errors yet
        assert handler.get_next_allowed_time("test") is None

        # Record error with retry-after
        handler.record_error("test", ErrorType.RATE_LIMITED, retry_after_seconds=60.0)
        next_time = handler.get_next_allowed_time("test")

        assert next_time is not None
        delta = next_time - datetime.now(UTC)
        assert 58 <= delta.total_seconds() <= 62

    def test_reset_endpoint(self) -> None:
        """Reset clears state for endpoint."""
        handler = BackoffHandler()
        handler.record_error("test", ErrorType.SERVER_ERROR)

        handler.reset_endpoint("test")

        state = handler.endpoint_states["test"]
        assert state.error_count == 0

    def test_reset_all(self) -> None:
        """Reset all clears all endpoint states."""
        handler = BackoffHandler()
        handler.record_error("test1", ErrorType.SERVER_ERROR)
        handler.record_error("test2", ErrorType.SERVER_ERROR)

        handler.reset_all()

        assert len(handler.endpoint_states) == 0

    def test_get_status(self) -> None:
        """Status returns comprehensive state."""
        handler = BackoffHandler()
        handler.record_error("test", ErrorType.SERVER_ERROR)

        status = handler.get_status()

        assert "config" in status
        assert "endpoints" in status
        assert "test" in status["endpoints"]
        assert status["endpoints"]["test"]["error_count"] == 1


class TestCreateBackoffHandler:
    """Tests for create_backoff_handler factory function."""

    def test_default_values(self) -> None:
        """Factory creates handler with defaults."""
        handler = create_backoff_handler()

        assert handler.config.base_delay == 1.0
        assert handler.config.max_delay == 300.0

    def test_custom_values(self) -> None:
        """Factory accepts custom values."""
        handler = create_backoff_handler(
            base_delay=2.0,
            max_delay=60.0,
        )

        assert handler.config.base_delay == 2.0
        assert handler.config.max_delay == 60.0
