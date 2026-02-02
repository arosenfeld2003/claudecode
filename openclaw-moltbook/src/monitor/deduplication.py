"""Content deduplication for Moltbook posts.

Implements deduplication to avoid processing the same content multiple times:
- Post ID tracking (primary key)
- Content hash tracking (SHA-256 of id:agent_id:title:submolt)

The deduplication check happens before processing to skip already-seen content.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def calculate_content_hash(
    post_id: str,
    agent_id: str,
    title: str,
    submolt: str,
) -> str:
    """Calculate SHA-256 content hash for a post.

    The hash is calculated from: {id}:{agent_id}:{title}:{submolt}

    This allows detecting duplicate content even if the post ID changes
    (e.g., reposts or cross-posts).

    Args:
        post_id: The post ID
        agent_id: The agent (author) ID
        title: The post title
        submolt: The submolt (community) name

    Returns:
        Hex-encoded SHA-256 hash string
    """
    content = f"{post_id}:{agent_id}:{title}:{submolt}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class SeenPost:
    """Record of a previously seen post."""

    post_id: str
    content_hash: str
    first_seen_at: datetime
    last_seen_at: datetime
    seen_count: int = 1


@dataclass
class DeduplicationTracker:
    """Tracks seen posts to avoid duplicate processing.

    Maintains two indexes:
    - By post ID (primary)
    - By content hash (for cross-post detection)

    Supports TTL-based expiration of old entries.

    Attributes:
        ttl: Time-to-live for entries (default: 90 days)
        by_id: Dict mapping post IDs to SeenPost records
        by_hash: Dict mapping content hashes to post IDs
    """

    ttl: timedelta = field(default_factory=lambda: timedelta(days=90))
    by_id: dict[str, SeenPost] = field(default_factory=dict)
    by_hash: dict[str, str] = field(default_factory=dict)

    def is_duplicate(
        self,
        post_id: str,
        content_hash: str | None = None,
    ) -> bool:
        """Check if a post has been seen before.

        Args:
            post_id: The post ID to check
            content_hash: Optional content hash to check for cross-posts

        Returns:
            True if the post (or its content) has been seen before
        """
        # Check by ID first
        if post_id in self.by_id:
            return True

        # Check by content hash if provided
        return bool(content_hash and content_hash in self.by_hash)

    def has_id(self, post_id: str) -> bool:
        """Check if a post ID has been seen.

        Args:
            post_id: The post ID to check

        Returns:
            True if the post ID has been seen
        """
        return post_id in self.by_id

    def has_hash(self, content_hash: str) -> bool:
        """Check if a content hash has been seen.

        Args:
            content_hash: The content hash to check

        Returns:
            True if the content hash has been seen
        """
        return content_hash in self.by_hash

    def mark_seen(
        self,
        post_id: str,
        content_hash: str,
    ) -> SeenPost:
        """Mark a post as seen.

        If the post was already seen (by ID), updates the last_seen_at timestamp
        and increments the seen_count.

        Args:
            post_id: The post ID
            content_hash: The content hash

        Returns:
            The SeenPost record (new or updated)
        """
        now = datetime.now(UTC)

        if post_id in self.by_id:
            # Update existing record
            record = self.by_id[post_id]
            record.last_seen_at = now
            record.seen_count += 1
            logger.debug(
                "Updated seen record for post %s (seen %d times)",
                post_id,
                record.seen_count,
            )
        else:
            # Create new record
            record = SeenPost(
                post_id=post_id,
                content_hash=content_hash,
                first_seen_at=now,
                last_seen_at=now,
                seen_count=1,
            )
            self.by_id[post_id] = record
            self.by_hash[content_hash] = post_id
            logger.debug("Marked post %s as seen", post_id)

        return record

    def get_by_id(self, post_id: str) -> SeenPost | None:
        """Get the SeenPost record for a post ID.

        Args:
            post_id: The post ID

        Returns:
            SeenPost record or None if not found
        """
        return self.by_id.get(post_id)

    def get_by_hash(self, content_hash: str) -> SeenPost | None:
        """Get the SeenPost record for a content hash.

        Args:
            content_hash: The content hash

        Returns:
            SeenPost record or None if not found
        """
        post_id = self.by_hash.get(content_hash)
        if post_id:
            return self.by_id.get(post_id)
        return None

    def cleanup_expired(self) -> int:
        """Remove expired entries based on TTL.

        Returns:
            Number of entries removed
        """
        now = datetime.now(UTC)
        cutoff = now - self.ttl
        removed = 0

        # Find expired entries
        expired_ids: list[str] = []
        for post_id, record in self.by_id.items():
            if record.last_seen_at < cutoff:
                expired_ids.append(post_id)

        # Remove expired entries
        for post_id in expired_ids:
            record = self.by_id.pop(post_id)
            self.by_hash.pop(record.content_hash, None)
            removed += 1

        if removed > 0:
            logger.info("Cleaned up %d expired deduplication entries", removed)

        return removed

    def get_stats(self) -> dict[str, Any]:
        """Get deduplication statistics.

        Returns:
            Dict with counts and oldest entry
        """
        oldest_seen = None
        if self.by_id:
            oldest_record = min(self.by_id.values(), key=lambda r: r.first_seen_at)
            oldest_seen = oldest_record.first_seen_at.isoformat()

        return {
            "total_posts": len(self.by_id),
            "total_hashes": len(self.by_hash),
            "oldest_entry": oldest_seen,
            "ttl_days": self.ttl.days,
        }

    def clear(self) -> None:
        """Clear all deduplication data."""
        self.by_id.clear()
        self.by_hash.clear()


@dataclass
class DeduplicationFilter:
    """Filter for deduplicating batches of posts.

    Combines the tracker with batch processing helpers.

    Attributes:
        tracker: The underlying DeduplicationTracker
    """

    tracker: DeduplicationTracker = field(default_factory=DeduplicationTracker)

    def filter_new(
        self,
        posts: list[dict[str, Any]],
        mark_seen: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """Filter a batch of posts to only include new ones.

        Args:
            posts: List of post dicts with at least 'id', 'agent_id', 'title', 'submolt'
            mark_seen: Whether to mark new posts as seen

        Returns:
            Tuple of (new posts list, skipped count)
        """
        new_posts: list[dict[str, Any]] = []
        skipped = 0

        for post in posts:
            post_id = str(post.get("id", ""))
            agent_id = str(post.get("agent_id", post.get("author_id", "")))
            title = post.get("title", "")
            submolt = post.get("submolt", "")

            content_hash = calculate_content_hash(post_id, agent_id, title, submolt)

            if self.tracker.is_duplicate(post_id, content_hash):
                skipped += 1
                continue

            new_posts.append(post)

            if mark_seen:
                self.tracker.mark_seen(post_id, content_hash)

        logger.info(
            "Deduplication: %d new, %d skipped (total: %d)",
            len(new_posts),
            skipped,
            len(posts),
        )

        return new_posts, skipped

    def is_new(self, post: dict[str, Any]) -> bool:
        """Check if a single post is new (not a duplicate).

        Args:
            post: Post dict with 'id', 'agent_id', 'title', 'submolt'

        Returns:
            True if the post is new
        """
        post_id = str(post.get("id", ""))
        agent_id = str(post.get("agent_id", post.get("author_id", "")))
        title = post.get("title", "")
        submolt = post.get("submolt", "")

        content_hash = calculate_content_hash(post_id, agent_id, title, submolt)

        return not self.tracker.is_duplicate(post_id, content_hash)

    def mark_post_seen(self, post: dict[str, Any]) -> SeenPost:
        """Mark a post as seen after processing.

        Args:
            post: Post dict with 'id', 'agent_id', 'title', 'submolt'

        Returns:
            The SeenPost record
        """
        post_id = str(post.get("id", ""))
        agent_id = str(post.get("agent_id", post.get("author_id", "")))
        title = post.get("title", "")
        submolt = post.get("submolt", "")

        content_hash = calculate_content_hash(post_id, agent_id, title, submolt)

        return self.tracker.mark_seen(post_id, content_hash)

    def cleanup(self) -> int:
        """Run cleanup of expired entries.

        Returns:
            Number of entries removed
        """
        return self.tracker.cleanup_expired()

    def get_stats(self) -> dict[str, Any]:
        """Get deduplication statistics."""
        return self.tracker.get_stats()


def create_deduplication_filter(ttl_days: int = 90) -> DeduplicationFilter:
    """Create a deduplication filter with the specified TTL.

    Args:
        ttl_days: Time-to-live for entries in days (default: 90)

    Returns:
        Configured DeduplicationFilter instance
    """
    tracker = DeduplicationTracker(ttl=timedelta(days=ttl_days))
    return DeduplicationFilter(tracker=tracker)
