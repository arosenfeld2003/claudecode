"""Tests for the deduplication module."""

from datetime import timedelta

import pytest

from monitor.deduplication import (
    DeduplicationFilter,
    DeduplicationTracker,
    SeenPost,
    calculate_content_hash,
    create_deduplication_filter,
)


class TestCalculateContentHash:
    """Tests for content hash calculation."""

    def test_consistent_hash(self) -> None:
        """Same input produces same hash."""
        hash1 = calculate_content_hash("id1", "agent1", "Title", "submolt")
        hash2 = calculate_content_hash("id1", "agent1", "Title", "submolt")

        assert hash1 == hash2

    def test_different_id_different_hash(self) -> None:
        """Different post ID produces different hash."""
        hash1 = calculate_content_hash("id1", "agent1", "Title", "submolt")
        hash2 = calculate_content_hash("id2", "agent1", "Title", "submolt")

        assert hash1 != hash2

    def test_different_agent_different_hash(self) -> None:
        """Different agent ID produces different hash."""
        hash1 = calculate_content_hash("id1", "agent1", "Title", "submolt")
        hash2 = calculate_content_hash("id1", "agent2", "Title", "submolt")

        assert hash1 != hash2

    def test_different_title_different_hash(self) -> None:
        """Different title produces different hash."""
        hash1 = calculate_content_hash("id1", "agent1", "Title 1", "submolt")
        hash2 = calculate_content_hash("id1", "agent1", "Title 2", "submolt")

        assert hash1 != hash2

    def test_different_submolt_different_hash(self) -> None:
        """Different submolt produces different hash."""
        hash1 = calculate_content_hash("id1", "agent1", "Title", "submolt1")
        hash2 = calculate_content_hash("id1", "agent1", "Title", "submolt2")

        assert hash1 != hash2

    def test_hash_is_sha256(self) -> None:
        """Hash is 64 character hex string (SHA-256)."""
        hash_value = calculate_content_hash("id", "agent", "title", "submolt")

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestSeenPost:
    """Tests for SeenPost dataclass."""

    def test_create_seen_post(self) -> None:
        """Create SeenPost record."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        post = SeenPost(
            post_id="id1",
            content_hash="hash1",
            first_seen_at=now,
            last_seen_at=now,
            seen_count=1,
        )

        assert post.post_id == "id1"
        assert post.content_hash == "hash1"
        assert post.seen_count == 1


class TestDeduplicationTracker:
    """Tests for DeduplicationTracker."""

    def test_is_duplicate_new_post(self) -> None:
        """New post is not a duplicate."""
        tracker = DeduplicationTracker()

        assert not tracker.is_duplicate("id1")
        assert not tracker.is_duplicate("id1", "hash1")

    def test_is_duplicate_by_id(self) -> None:
        """Post is duplicate if ID was seen."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")

        assert tracker.is_duplicate("id1")
        assert tracker.is_duplicate("id1", "different_hash")

    def test_is_duplicate_by_hash(self) -> None:
        """Post is duplicate if content hash was seen."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")

        # Different ID but same hash
        assert tracker.is_duplicate("id2", "hash1")

    def test_mark_seen_creates_record(self) -> None:
        """mark_seen creates a SeenPost record."""
        tracker = DeduplicationTracker()
        record = tracker.mark_seen("id1", "hash1")

        assert record.post_id == "id1"
        assert record.content_hash == "hash1"
        assert record.seen_count == 1

    def test_mark_seen_updates_existing(self) -> None:
        """mark_seen updates existing record."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")
        record = tracker.mark_seen("id1", "hash1")

        assert record.seen_count == 2
        assert record.last_seen_at >= record.first_seen_at

    def test_has_id(self) -> None:
        """has_id checks ID index."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")

        assert tracker.has_id("id1")
        assert not tracker.has_id("id2")

    def test_has_hash(self) -> None:
        """has_hash checks hash index."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")

        assert tracker.has_hash("hash1")
        assert not tracker.has_hash("hash2")

    def test_get_by_id(self) -> None:
        """get_by_id retrieves record by ID."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")

        record = tracker.get_by_id("id1")
        assert record is not None
        assert record.post_id == "id1"

        assert tracker.get_by_id("id2") is None

    def test_get_by_hash(self) -> None:
        """get_by_hash retrieves record by content hash."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")

        record = tracker.get_by_hash("hash1")
        assert record is not None
        assert record.content_hash == "hash1"

        assert tracker.get_by_hash("hash2") is None

    def test_cleanup_expired(self) -> None:
        """cleanup_expired removes old entries."""
        from datetime import UTC, datetime

        tracker = DeduplicationTracker(ttl=timedelta(days=1))

        # Add entry with old last_seen_at
        record = tracker.mark_seen("id1", "hash1")
        # Manually backdate it
        record.last_seen_at = datetime.now(UTC) - timedelta(days=2)

        removed = tracker.cleanup_expired()

        assert removed == 1
        assert not tracker.has_id("id1")
        assert not tracker.has_hash("hash1")

    def test_get_stats(self) -> None:
        """get_stats returns tracker statistics."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")
        tracker.mark_seen("id2", "hash2")

        stats = tracker.get_stats()

        assert stats["total_posts"] == 2
        assert stats["total_hashes"] == 2
        assert stats["oldest_entry"] is not None

    def test_clear(self) -> None:
        """clear removes all entries."""
        tracker = DeduplicationTracker()
        tracker.mark_seen("id1", "hash1")
        tracker.mark_seen("id2", "hash2")

        tracker.clear()

        assert len(tracker.by_id) == 0
        assert len(tracker.by_hash) == 0


class TestDeduplicationFilter:
    """Tests for DeduplicationFilter."""

    def test_filter_new_posts(self) -> None:
        """filter_new returns only new posts."""
        filter = DeduplicationFilter()

        posts = [
            {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"},
            {"id": "2", "agent_id": "a1", "title": "Post 2", "submolt": "test"},
        ]

        new_posts, skipped = filter.filter_new(posts)

        assert len(new_posts) == 2
        assert skipped == 0

    def test_filter_new_skips_duplicates(self) -> None:
        """filter_new skips already seen posts."""
        filter = DeduplicationFilter()

        posts1 = [
            {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"},
        ]
        filter.filter_new(posts1)

        # Same post again plus a new one
        posts2 = [
            {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"},
            {"id": "2", "agent_id": "a1", "title": "Post 2", "submolt": "test"},
        ]
        new_posts, skipped = filter.filter_new(posts2)

        assert len(new_posts) == 1
        assert new_posts[0]["id"] == "2"
        assert skipped == 1

    def test_filter_new_without_marking(self) -> None:
        """filter_new can skip marking posts as seen."""
        filter = DeduplicationFilter()

        posts = [
            {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"},
        ]

        # First call without marking
        new_posts1, _ = filter.filter_new(posts, mark_seen=False)
        # Second call should still see it as new
        new_posts2, _ = filter.filter_new(posts, mark_seen=True)

        assert len(new_posts1) == 1
        assert len(new_posts2) == 1

        # Third call should skip it
        new_posts3, skipped = filter.filter_new(posts)
        assert len(new_posts3) == 0
        assert skipped == 1

    def test_is_new(self) -> None:
        """is_new checks single post."""
        filter = DeduplicationFilter()

        post = {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"}

        assert filter.is_new(post)
        filter.mark_post_seen(post)
        assert not filter.is_new(post)

    def test_mark_post_seen(self) -> None:
        """mark_post_seen marks a single post."""
        filter = DeduplicationFilter()

        post = {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"}
        record = filter.mark_post_seen(post)

        assert record.post_id == "1"
        assert not filter.is_new(post)

    def test_cleanup(self) -> None:
        """cleanup removes expired entries."""
        filter = DeduplicationFilter()
        filter.tracker.ttl = timedelta(days=1)

        # Add old entry
        from datetime import UTC, datetime

        post = {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"}
        record = filter.mark_post_seen(post)
        record.last_seen_at = datetime.now(UTC) - timedelta(days=2)

        removed = filter.cleanup()
        assert removed == 1

    def test_get_stats(self) -> None:
        """get_stats returns statistics."""
        filter = DeduplicationFilter()
        filter.mark_post_seen(
            {"id": "1", "agent_id": "a1", "title": "Post 1", "submolt": "test"}
        )

        stats = filter.get_stats()

        assert stats["total_posts"] == 1

    def test_handles_author_id_field(self) -> None:
        """Filter handles author_id as alternative to agent_id."""
        filter = DeduplicationFilter()

        post = {"id": "1", "author_id": "a1", "title": "Post 1", "submolt": "test"}

        assert filter.is_new(post)
        filter.mark_post_seen(post)
        assert not filter.is_new(post)


class TestCreateDeduplicationFilter:
    """Tests for create_deduplication_filter factory function."""

    def test_default_ttl(self) -> None:
        """Factory creates filter with default TTL."""
        filter = create_deduplication_filter()

        assert filter.tracker.ttl == timedelta(days=90)

    def test_custom_ttl(self) -> None:
        """Factory accepts custom TTL."""
        filter = create_deduplication_filter(ttl_days=30)

        assert filter.tracker.ttl == timedelta(days=30)
