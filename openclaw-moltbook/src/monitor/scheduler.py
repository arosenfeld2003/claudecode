"""Polling scheduler for Moltbook API monitoring.

Implements adaptive polling with:
- Default intervals per endpoint type
- Adaptive intervals based on activity rate
- Spike detection for increased polling frequency
- Graceful shutdown with state persistence
- APScheduler integration for job management

Default intervals:
- /posts?sort=new: 5 minutes
- /posts?sort=hot: 15 minutes
- /posts?sort=top: 1 hour
- /submolts: 6 hours
- /posts/:id/comments: on-demand
- /agents/profile: on-demand

Adaptive behavior:
- High activity (>10 posts/min): Increase frequency (min 1 minute)
- Low activity (<1 post/min): Decrease frequency (max 30 minutes)
"""

import asyncio
import logging
import signal
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class EndpointType(str, Enum):
    """Types of API endpoints for polling."""

    NEW_POSTS = "new_posts"
    HOT_POSTS = "hot_posts"
    TOP_POSTS = "top_posts"
    RISING_POSTS = "rising_posts"
    SUBMOLTS = "submolts"
    COMMENTS = "comments"  # On-demand
    AGENTS = "agents"  # On-demand


@dataclass
class PollingInterval:
    """Polling interval configuration for an endpoint."""

    default: timedelta
    minimum: timedelta
    maximum: timedelta


# Default polling intervals per endpoint type
DEFAULT_INTERVALS: dict[EndpointType, PollingInterval] = {
    EndpointType.NEW_POSTS: PollingInterval(
        default=timedelta(minutes=5),
        minimum=timedelta(minutes=1),
        maximum=timedelta(minutes=30),
    ),
    EndpointType.HOT_POSTS: PollingInterval(
        default=timedelta(minutes=15),
        minimum=timedelta(minutes=5),
        maximum=timedelta(hours=1),
    ),
    EndpointType.TOP_POSTS: PollingInterval(
        default=timedelta(hours=1),
        minimum=timedelta(minutes=15),
        maximum=timedelta(hours=6),
    ),
    EndpointType.RISING_POSTS: PollingInterval(
        default=timedelta(minutes=10),
        minimum=timedelta(minutes=2),
        maximum=timedelta(minutes=30),
    ),
    EndpointType.SUBMOLTS: PollingInterval(
        default=timedelta(hours=6),
        minimum=timedelta(hours=1),
        maximum=timedelta(hours=24),
    ),
}


@dataclass
class PollState:
    """State for a polling endpoint."""

    endpoint: EndpointType
    last_post_id: str | None = None
    last_poll_at: datetime | None = None
    next_poll_at: datetime | None = None
    current_interval: timedelta | None = None
    error_count: int = 0
    last_error: str | None = None
    posts_fetched_last: int = 0
    total_posts_fetched: int = 0

    def record_poll(
        self,
        posts_fetched: int,
        last_post_id: str | None = None,
        interval: timedelta | None = None,
    ) -> None:
        """Record a successful poll."""
        now = datetime.now(UTC)
        self.last_poll_at = now
        self.posts_fetched_last = posts_fetched
        self.total_posts_fetched += posts_fetched
        self.error_count = 0
        self.last_error = None

        if last_post_id:
            self.last_post_id = last_post_id

        if interval:
            self.current_interval = interval
            self.next_poll_at = now + interval

    def record_error(self, error: str) -> None:
        """Record a poll error."""
        self.error_count += 1
        self.last_error = error


@dataclass
class ActivityTracker:
    """Tracks activity rates for adaptive polling.

    Maintains a sliding window of post counts to calculate
    activity rates and detect spikes.

    Attributes:
        window_size: Size of the sliding window (default: 1 hour)
        samples: List of (timestamp, count) tuples
    """

    window_size: timedelta = field(default_factory=lambda: timedelta(hours=1))
    samples: list[tuple[datetime, int]] = field(default_factory=list)

    def record_activity(self, count: int) -> None:
        """Record an activity sample."""
        now = datetime.now(UTC)
        self.samples.append((now, count))
        self._cleanup_old_samples()

    def _cleanup_old_samples(self) -> None:
        """Remove samples outside the window."""
        cutoff = datetime.now(UTC) - self.window_size
        self.samples = [(ts, count) for ts, count in self.samples if ts > cutoff]

    def get_rate(self) -> float:
        """Get the current activity rate (posts per minute).

        Returns:
            Average posts per minute over the window
        """
        self._cleanup_old_samples()

        if not self.samples:
            return 0.0

        total_count = sum(count for _, count in self.samples)
        time_span = (
            self.samples[-1][0] - self.samples[0][0]
        ).total_seconds() / 60.0

        if time_span <= 0:
            return float(total_count)

        return total_count / time_span

    def is_high_activity(self, threshold: float = 10.0) -> bool:
        """Check if activity rate is high (above threshold).

        Args:
            threshold: Posts per minute threshold (default: 10)
        """
        return self.get_rate() > threshold

    def is_low_activity(self, threshold: float = 1.0) -> bool:
        """Check if activity rate is low (below threshold).

        Args:
            threshold: Posts per minute threshold (default: 1)
        """
        return self.get_rate() < threshold

    def is_spiking(self, multiplier: float = 3.0) -> bool:
        """Check if current activity is spiking (significantly above normal).

        A spike is detected when the most recent sample rate is
        significantly higher than the historical average.

        Args:
            multiplier: How many times above normal to consider a spike
        """
        self._cleanup_old_samples()

        if len(self.samples) < 3:
            return False

        # Calculate average rate (excluding most recent)
        historical = self.samples[:-1]
        historical_total = sum(count for _, count in historical)
        historical_span = (
            historical[-1][0] - historical[0][0]
        ).total_seconds() / 60.0

        if historical_span <= 0:
            return False

        historical_rate = historical_total / historical_span

        # Get most recent rate
        recent_count = self.samples[-1][1]

        # Compare with historical (use 10 as minimum baseline)
        baseline = max(historical_rate, 10)
        return recent_count > baseline * multiplier


@dataclass
class PollingScheduler:
    """Scheduler for API polling jobs.

    Manages polling schedules with adaptive intervals and
    graceful shutdown.

    Attributes:
        poll_states: State for each endpoint type
        activity_tracker: Tracks activity for adaptive polling
        scheduler: APScheduler instance
        poll_callback: Callback function for poll execution
        shutdown_event: Event for graceful shutdown
    """

    poll_states: dict[EndpointType, PollState] = field(default_factory=dict)
    activity_tracker: ActivityTracker = field(default_factory=ActivityTracker)
    scheduler: BackgroundScheduler | None = field(default=None, repr=False)
    poll_callback: Callable[[EndpointType], None] | None = field(
        default=None, repr=False
    )
    shutdown_event: threading.Event = field(default_factory=threading.Event, repr=False)
    _running: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize poll states."""
        for endpoint_type in EndpointType:
            if endpoint_type not in self.poll_states:
                self.poll_states[endpoint_type] = PollState(endpoint=endpoint_type)

    def _get_adaptive_interval(self, endpoint_type: EndpointType) -> timedelta:
        """Calculate adaptive interval based on activity.

        Args:
            endpoint_type: The endpoint type

        Returns:
            Adjusted polling interval
        """
        config = DEFAULT_INTERVALS.get(endpoint_type)
        if config is None:
            return timedelta(minutes=5)

        base_interval = config.default

        # Adjust based on activity
        if self.activity_tracker.is_spiking():
            # During spikes, use minimum interval
            return config.minimum
        elif self.activity_tracker.is_high_activity():
            # High activity: reduce interval
            reduced = base_interval * 0.5
            return max(reduced, config.minimum)
        elif self.activity_tracker.is_low_activity():
            # Low activity: increase interval
            increased = base_interval * 2
            return min(increased, config.maximum)

        return base_interval

    def _create_poll_job(self, endpoint_type: EndpointType) -> Callable[[], None]:
        """Create a poll job function for an endpoint.

        Args:
            endpoint_type: The endpoint type

        Returns:
            Job function to execute
        """

        def job() -> None:
            if self.shutdown_event.is_set():
                return

            if self.poll_callback:
                try:
                    self.poll_callback(endpoint_type)
                except Exception as e:
                    logger.exception("Error in poll callback for %s: %s", endpoint_type, e)
                    state = self.poll_states[endpoint_type]
                    state.record_error(str(e))

            # Update interval based on activity
            self._update_job_interval(endpoint_type)

        return job

    def _update_job_interval(self, endpoint_type: EndpointType) -> None:
        """Update the polling interval for an endpoint job.

        Args:
            endpoint_type: The endpoint type
        """
        if self.scheduler is None:
            return

        job_id = f"poll_{endpoint_type.value}"
        new_interval = self._get_adaptive_interval(endpoint_type)

        # Reschedule with new interval
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.reschedule_job(
                job_id,
                trigger=IntervalTrigger(seconds=new_interval.total_seconds()),
            )

        # Update state
        state = self.poll_states[endpoint_type]
        state.current_interval = new_interval
        state.next_poll_at = datetime.now(UTC) + new_interval

        logger.debug(
            "Updated interval for %s: %s",
            endpoint_type.value,
            new_interval,
        )

    def start(self, poll_callback: Callable[[EndpointType], None]) -> None:
        """Start the polling scheduler.

        Args:
            poll_callback: Callback function to execute for each poll
        """
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self.poll_callback = poll_callback
        self.shutdown_event.clear()

        # Create scheduler
        self.scheduler = BackgroundScheduler()

        # Schedule jobs for scheduled endpoint types (not on-demand)
        for endpoint_type in [
            EndpointType.NEW_POSTS,
            EndpointType.HOT_POSTS,
            EndpointType.TOP_POSTS,
            EndpointType.RISING_POSTS,
            EndpointType.SUBMOLTS,
        ]:
            interval = DEFAULT_INTERVALS[endpoint_type].default
            job_id = f"poll_{endpoint_type.value}"

            self.scheduler.add_job(
                self._create_poll_job(endpoint_type),
                trigger=IntervalTrigger(seconds=interval.total_seconds()),
                id=job_id,
                name=f"Poll {endpoint_type.value}",
                replace_existing=True,
            )

            logger.info(
                "Scheduled %s polling every %s",
                endpoint_type.value,
                interval,
            )

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Start scheduler
        self.scheduler.start()
        self._running = True

        logger.info("Polling scheduler started")

    def stop(self, wait: bool = True) -> None:
        """Stop the polling scheduler gracefully.

        Args:
            wait: Whether to wait for current jobs to complete
        """
        if not self._running:
            return

        logger.info("Stopping polling scheduler...")

        # Signal shutdown
        self.shutdown_event.set()

        # Shutdown scheduler
        if self.scheduler:
            self.scheduler.shutdown(wait=wait)
            self.scheduler = None

        self._running = False

        logger.info("Polling scheduler stopped")

    def _handle_signal(self, signum: int, frame: Any) -> None:  # noqa: ARG002
        """Handle shutdown signals."""
        logger.info("Received signal %d, initiating graceful shutdown", signum)
        self.stop()

    def record_poll_result(
        self,
        endpoint_type: EndpointType,
        posts_fetched: int,
        last_post_id: str | None = None,
    ) -> None:
        """Record the result of a poll.

        Args:
            endpoint_type: The endpoint type that was polled
            posts_fetched: Number of posts fetched
            last_post_id: ID of the last post fetched
        """
        state = self.poll_states[endpoint_type]
        interval = self._get_adaptive_interval(endpoint_type)
        state.record_poll(posts_fetched, last_post_id, interval)

        # Update activity tracker
        self.activity_tracker.record_activity(posts_fetched)

    def record_poll_error(self, endpoint_type: EndpointType, error: str) -> None:
        """Record a poll error.

        Args:
            endpoint_type: The endpoint type that failed
            error: Error message
        """
        state = self.poll_states[endpoint_type]
        state.record_error(error)

    def trigger_poll(self, endpoint_type: EndpointType) -> None:
        """Trigger an immediate poll for an endpoint.

        Used for on-demand endpoints (comments, agents) or
        manual refresh requests.

        Args:
            endpoint_type: The endpoint type to poll
        """
        if self.poll_callback:
            try:
                self.poll_callback(endpoint_type)
            except Exception as e:
                logger.exception("Error in manual poll for %s: %s", endpoint_type, e)
                self.record_poll_error(endpoint_type, str(e))

    def get_status(self) -> dict[str, Any]:
        """Get current scheduler status.

        Returns:
            Dict with scheduler state and poll states
        """
        return {
            "running": self._running,
            "activity_rate": self.activity_tracker.get_rate(),
            "is_spiking": self.activity_tracker.is_spiking(),
            "poll_states": {
                endpoint_type.value: {
                    "last_post_id": state.last_post_id,
                    "last_poll_at": (
                        state.last_poll_at.isoformat() if state.last_poll_at else None
                    ),
                    "next_poll_at": (
                        state.next_poll_at.isoformat() if state.next_poll_at else None
                    ),
                    "current_interval": (
                        state.current_interval.total_seconds()
                        if state.current_interval
                        else None
                    ),
                    "error_count": state.error_count,
                    "last_error": state.last_error,
                    "posts_fetched_last": state.posts_fetched_last,
                    "total_posts_fetched": state.total_posts_fetched,
                }
                for endpoint_type, state in self.poll_states.items()
            },
        }

    def get_state_for_persistence(self) -> dict[str, Any]:
        """Get state in a format suitable for persistence.

        Returns:
            Dict with poll states to save
        """
        return {
            endpoint_type.value: {
                "last_post_id": state.last_post_id,
                "last_poll_at": (
                    state.last_poll_at.isoformat() if state.last_poll_at else None
                ),
                "error_count": state.error_count,
                "total_posts_fetched": state.total_posts_fetched,
            }
            for endpoint_type, state in self.poll_states.items()
        }

    def restore_state(self, state_data: dict[str, Any]) -> None:
        """Restore poll state from persisted data.

        Args:
            state_data: Previously saved state dict
        """
        for endpoint_name, data in state_data.items():
            try:
                endpoint_type = EndpointType(endpoint_name)
                state = self.poll_states.get(endpoint_type)
                if state:
                    state.last_post_id = data.get("last_post_id")
                    if data.get("last_poll_at"):
                        state.last_poll_at = datetime.fromisoformat(
                            data["last_poll_at"]
                        )
                    state.error_count = data.get("error_count", 0)
                    state.total_posts_fetched = data.get("total_posts_fetched", 0)
            except (ValueError, KeyError) as e:
                logger.warning("Error restoring state for %s: %s", endpoint_name, e)

        logger.info("Restored poll state from persistence")


def create_scheduler() -> PollingScheduler:
    """Create a new polling scheduler instance.

    Returns:
        Configured PollingScheduler instance
    """
    return PollingScheduler()


async def run_scheduler_async(
    scheduler: PollingScheduler,
    poll_callback: Callable[[EndpointType], None],
) -> None:
    """Run the scheduler in an async context.

    This allows integration with async code while the scheduler
    runs its background threads.

    Args:
        scheduler: The scheduler instance
        poll_callback: Callback function for polls
    """
    scheduler.start(poll_callback)

    try:
        # Keep running until shutdown
        while not scheduler.shutdown_event.is_set():
            await asyncio.sleep(1.0)
    finally:
        scheduler.stop()
