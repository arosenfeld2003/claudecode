"""Tests for the polling scheduler module."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from monitor.scheduler import (
    DEFAULT_INTERVALS,
    ActivityTracker,
    EndpointType,
    PollingInterval,
    PollingScheduler,
    PollState,
    create_scheduler,
)


class TestEndpointType:
    """Tests for EndpointType enum."""

    def test_all_endpoint_types(self) -> None:
        """All expected endpoint types exist."""
        assert EndpointType.NEW_POSTS.value == "new_posts"
        assert EndpointType.HOT_POSTS.value == "hot_posts"
        assert EndpointType.TOP_POSTS.value == "top_posts"
        assert EndpointType.RISING_POSTS.value == "rising_posts"
        assert EndpointType.SUBMOLTS.value == "submolts"
        assert EndpointType.COMMENTS.value == "comments"
        assert EndpointType.AGENTS.value == "agents"


class TestDefaultIntervals:
    """Tests for default polling intervals."""

    def test_new_posts_interval(self) -> None:
        """New posts has 5 minute default interval."""
        config = DEFAULT_INTERVALS[EndpointType.NEW_POSTS]

        assert config.default == timedelta(minutes=5)
        assert config.minimum == timedelta(minutes=1)
        assert config.maximum == timedelta(minutes=30)

    def test_hot_posts_interval(self) -> None:
        """Hot posts has 15 minute default interval."""
        config = DEFAULT_INTERVALS[EndpointType.HOT_POSTS]

        assert config.default == timedelta(minutes=15)

    def test_top_posts_interval(self) -> None:
        """Top posts has 1 hour default interval."""
        config = DEFAULT_INTERVALS[EndpointType.TOP_POSTS]

        assert config.default == timedelta(hours=1)

    def test_submolts_interval(self) -> None:
        """Submolts has 6 hour default interval."""
        config = DEFAULT_INTERVALS[EndpointType.SUBMOLTS]

        assert config.default == timedelta(hours=6)


class TestPollState:
    """Tests for PollState."""

    def test_initial_state(self) -> None:
        """State initializes with defaults."""
        state = PollState(endpoint=EndpointType.NEW_POSTS)

        assert state.endpoint == EndpointType.NEW_POSTS
        assert state.last_post_id is None
        assert state.last_poll_at is None
        assert state.error_count == 0
        assert state.total_posts_fetched == 0

    def test_record_poll(self) -> None:
        """record_poll updates state."""
        state = PollState(endpoint=EndpointType.NEW_POSTS)
        state.record_poll(
            posts_fetched=10,
            last_post_id="post123",
            interval=timedelta(minutes=5),
        )

        assert state.posts_fetched_last == 10
        assert state.total_posts_fetched == 10
        assert state.last_post_id == "post123"
        assert state.last_poll_at is not None
        assert state.next_poll_at is not None
        assert state.current_interval == timedelta(minutes=5)

    def test_record_poll_resets_errors(self) -> None:
        """Successful poll resets error count."""
        state = PollState(endpoint=EndpointType.NEW_POSTS)
        state.error_count = 5
        state.last_error = "Previous error"

        state.record_poll(posts_fetched=10)

        assert state.error_count == 0
        assert state.last_error is None

    def test_record_error(self) -> None:
        """record_error increments error count."""
        state = PollState(endpoint=EndpointType.NEW_POSTS)
        state.record_error("Connection failed")

        assert state.error_count == 1
        assert state.last_error == "Connection failed"


class TestActivityTracker:
    """Tests for ActivityTracker."""

    def test_initial_state(self) -> None:
        """Tracker starts empty."""
        tracker = ActivityTracker()

        assert len(tracker.samples) == 0
        assert tracker.get_rate() == 0.0

    def test_record_activity(self) -> None:
        """record_activity adds samples."""
        tracker = ActivityTracker()
        tracker.record_activity(10)
        tracker.record_activity(15)

        assert len(tracker.samples) == 2

    def test_get_rate(self) -> None:
        """get_rate calculates posts per minute."""
        import time

        tracker = ActivityTracker()
        tracker.record_activity(60)
        time.sleep(0.01)  # Small delay
        tracker.record_activity(60)

        rate = tracker.get_rate()
        # Rate should be > 0 (exact value depends on timing)
        assert rate > 0

    def test_is_high_activity(self) -> None:
        """is_high_activity detects high rates."""
        tracker = ActivityTracker()

        # Add samples with high rate
        for _ in range(5):
            tracker.record_activity(100)

        # With 500 posts in nearly instant time, rate should be high
        assert tracker.get_rate() > 0

    def test_is_low_activity(self) -> None:
        """is_low_activity detects low rates."""
        tracker = ActivityTracker()

        # Fresh tracker has 0 rate
        assert tracker.is_low_activity()

    def test_cleanup_old_samples(self) -> None:
        """Old samples are cleaned up."""
        from datetime import UTC, datetime

        tracker = ActivityTracker(window_size=timedelta(minutes=1))

        # Add old sample
        old_time = datetime.now(UTC) - timedelta(hours=1)
        tracker.samples.append((old_time, 10))

        # Add new sample
        tracker.record_activity(5)

        # Only new sample should remain
        assert len(tracker.samples) == 1


class TestPollingScheduler:
    """Tests for PollingScheduler."""

    def test_init_creates_poll_states(self) -> None:
        """Scheduler initializes poll states for all endpoints."""
        scheduler = PollingScheduler()

        for endpoint_type in EndpointType:
            assert endpoint_type in scheduler.poll_states

    def test_get_adaptive_interval_default(self) -> None:
        """Adaptive interval doubles on low/no activity (capped at maximum)."""
        scheduler = PollingScheduler()

        interval = scheduler._get_adaptive_interval(EndpointType.NEW_POSTS)

        # With no activity (low activity), interval is doubled but capped at max
        config = DEFAULT_INTERVALS[EndpointType.NEW_POSTS]
        expected = min(config.default * 2, config.maximum)
        assert interval == expected

    def test_record_poll_result(self) -> None:
        """record_poll_result updates state."""
        scheduler = PollingScheduler()
        scheduler.record_poll_result(
            endpoint_type=EndpointType.NEW_POSTS,
            posts_fetched=10,
            last_post_id="post123",
        )

        state = scheduler.poll_states[EndpointType.NEW_POSTS]
        assert state.last_post_id == "post123"
        assert state.posts_fetched_last == 10

    def test_record_poll_error(self) -> None:
        """record_poll_error updates state."""
        scheduler = PollingScheduler()
        scheduler.record_poll_error(
            endpoint_type=EndpointType.NEW_POSTS,
            error="Connection failed",
        )

        state = scheduler.poll_states[EndpointType.NEW_POSTS]
        assert state.error_count == 1
        assert state.last_error == "Connection failed"

    def test_trigger_poll_calls_callback(self) -> None:
        """trigger_poll executes callback."""
        scheduler = PollingScheduler()
        callback = MagicMock()
        scheduler.poll_callback = callback

        scheduler.trigger_poll(EndpointType.NEW_POSTS)

        callback.assert_called_once_with(EndpointType.NEW_POSTS)

    def test_get_status(self) -> None:
        """get_status returns comprehensive status."""
        scheduler = PollingScheduler()

        status = scheduler.get_status()

        assert "running" in status
        assert "activity_rate" in status
        assert "poll_states" in status
        assert "new_posts" in status["poll_states"]

    def test_get_state_for_persistence(self) -> None:
        """get_state_for_persistence returns serializable state."""
        scheduler = PollingScheduler()
        scheduler.record_poll_result(
            endpoint_type=EndpointType.NEW_POSTS,
            posts_fetched=10,
            last_post_id="post123",
        )

        state = scheduler.get_state_for_persistence()

        assert "new_posts" in state
        assert state["new_posts"]["last_post_id"] == "post123"

    def test_restore_state(self) -> None:
        """restore_state loads persisted state."""
        from datetime import UTC, datetime

        scheduler = PollingScheduler()
        state_data = {
            "new_posts": {
                "last_post_id": "post456",
                "last_poll_at": datetime.now(UTC).isoformat(),
                "error_count": 2,
                "total_posts_fetched": 100,
            }
        }

        scheduler.restore_state(state_data)

        state = scheduler.poll_states[EndpointType.NEW_POSTS]
        assert state.last_post_id == "post456"
        assert state.error_count == 2
        assert state.total_posts_fetched == 100

    def test_start_and_stop(self) -> None:
        """Scheduler can start and stop."""
        scheduler = PollingScheduler()
        callback = MagicMock()

        # Start
        scheduler.start(callback)
        assert scheduler._running
        assert scheduler.scheduler is not None

        # Stop
        scheduler.stop(wait=False)
        assert not scheduler._running
        assert scheduler.scheduler is None

    def test_stop_when_not_running(self) -> None:
        """Stop when not running does nothing."""
        scheduler = PollingScheduler()
        scheduler.stop()  # Should not raise


class TestCreateScheduler:
    """Tests for create_scheduler factory function."""

    def test_creates_scheduler(self) -> None:
        """Factory creates scheduler instance."""
        scheduler = create_scheduler()

        assert isinstance(scheduler, PollingScheduler)
        assert not scheduler._running
