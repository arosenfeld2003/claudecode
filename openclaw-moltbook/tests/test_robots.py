"""Tests for the robots.txt compliance module."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from monitor.robots import (
    RobotsCache,
    RobotsChecker,
    RobotsDirectives,
    RobotsRule,
    create_robots_checker,
)


class TestRobotsRule:
    """Tests for RobotsRule matching."""

    def test_exact_match(self) -> None:
        """Rule matches exact path."""
        rule = RobotsRule(path="/admin/", allow=False)

        assert rule.matches("/admin/")
        assert rule.matches("/admin/settings")
        assert not rule.matches("/public/")

    def test_prefix_match(self) -> None:
        """Rule matches path prefix."""
        rule = RobotsRule(path="/api", allow=False)

        assert rule.matches("/api")
        assert rule.matches("/api/v1")
        assert rule.matches("/api/v1/posts")
        assert not rule.matches("/public")

    def test_wildcard_match(self) -> None:
        """Rule matches wildcard patterns."""
        rule = RobotsRule(path="/*/private/", allow=False)

        assert rule.matches("/user/private/")
        assert rule.matches("/admin/private/settings")

    def test_end_anchor(self) -> None:
        """Rule respects $ end anchor."""
        rule = RobotsRule(path="/page$", allow=False)

        assert rule.matches("/page")
        assert not rule.matches("/page/subpage")


class TestRobotsDirectives:
    """Tests for RobotsDirectives."""

    def test_empty_rules_allows_all(self) -> None:
        """Empty rules allow all paths."""
        directives = RobotsDirectives(user_agent="*")

        assert directives.is_allowed("/any/path")
        assert directives.is_allowed("/")

    def test_disallow_rule(self) -> None:
        """Disallow rules block paths."""
        directives = RobotsDirectives(
            user_agent="*",
            rules=[
                RobotsRule(path="/admin/", allow=False),
            ],
        )

        assert not directives.is_allowed("/admin/")
        assert not directives.is_allowed("/admin/settings")
        assert directives.is_allowed("/public/")

    def test_allow_overrides_disallow(self) -> None:
        """Allow rules can override disallow (first match wins)."""
        directives = RobotsDirectives(
            user_agent="*",
            rules=[
                RobotsRule(path="/admin/public/", allow=True),
                RobotsRule(path="/admin/", allow=False),
            ],
        )

        assert directives.is_allowed("/admin/public/")
        assert not directives.is_allowed("/admin/settings")

    def test_crawl_delay(self) -> None:
        """Directives can have crawl delay."""
        directives = RobotsDirectives(
            user_agent="*",
            crawl_delay=5.0,
        )

        assert directives.crawl_delay == 5.0


class TestRobotsChecker:
    """Tests for RobotsChecker."""

    def test_parse_simple_robots_txt(self) -> None:
        """Parse simple robots.txt content."""
        checker = RobotsChecker()

        content = """
User-agent: *
Disallow: /admin/
Allow: /admin/login
Crawl-delay: 5
"""
        directives = checker._parse_robots_txt(content)

        assert len(directives) == 1
        assert directives[0].user_agent == "*"
        assert len(directives[0].rules) == 2
        assert directives[0].crawl_delay == 5.0

    def test_parse_multiple_user_agents(self) -> None:
        """Parse robots.txt with multiple user-agent blocks."""
        checker = RobotsChecker()

        content = """
User-agent: GoogleBot
Disallow: /private/

User-agent: *
Disallow: /admin/
"""
        directives = checker._parse_robots_txt(content)

        assert len(directives) == 2
        assert directives[0].user_agent == "GoogleBot"
        assert directives[1].user_agent == "*"

    def test_parse_sitemaps(self) -> None:
        """Parse sitemap entries from robots.txt."""
        checker = RobotsChecker()

        content = """
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap2.xml
"""
        directives = checker._parse_robots_txt(content)

        assert len(directives) == 1
        assert len(directives[0].sitemaps) == 2

    def test_parse_comments_ignored(self) -> None:
        """Comments in robots.txt are ignored."""
        checker = RobotsChecker()

        content = """
# This is a comment
User-agent: *
Disallow: /admin/  # Inline comment
"""
        directives = checker._parse_robots_txt(content)

        assert len(directives) == 1
        assert len(directives[0].rules) == 1

    def test_find_matching_directives_exact(self) -> None:
        """Find exact user-agent match."""
        checker = RobotsChecker(user_agent="OpenClawMonitor")

        directives = [
            RobotsDirectives(user_agent="GoogleBot"),
            RobotsDirectives(user_agent="OpenClawMonitor"),
            RobotsDirectives(user_agent="*"),
        ]

        match = checker._find_matching_directives(directives)

        assert match is not None
        assert match.user_agent == "OpenClawMonitor"

    def test_find_matching_directives_wildcard(self) -> None:
        """Fall back to wildcard user-agent."""
        checker = RobotsChecker(user_agent="OpenClawMonitor")

        directives = [
            RobotsDirectives(user_agent="GoogleBot"),
            RobotsDirectives(user_agent="*"),
        ]

        match = checker._find_matching_directives(directives)

        assert match is not None
        assert match.user_agent == "*"

    def test_find_matching_directives_none(self) -> None:
        """Return None if no matching user-agent."""
        checker = RobotsChecker(user_agent="OpenClawMonitor")

        directives = [
            RobotsDirectives(user_agent="GoogleBot"),
            RobotsDirectives(user_agent="BingBot"),
        ]

        match = checker._find_matching_directives(directives)

        assert match is None

    @patch.object(httpx.Client, "get")
    def test_fetch_robots_txt_success(self, mock_get: MagicMock) -> None:
        """Successfully fetch and parse robots.txt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow: /admin/
"""
        mock_get.return_value = mock_response

        checker = RobotsChecker()
        cache = checker.fetch_robots_txt("https://example.com")

        assert cache is not None
        assert len(cache.directives) == 1
        assert "https://example.com" in checker.cache

    @patch.object(httpx.Client, "get")
    def test_fetch_robots_txt_404(self, mock_get: MagicMock) -> None:
        """Handle 404 (no robots.txt) by allowing all."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        checker = RobotsChecker()
        cache = checker.fetch_robots_txt("https://example.com")

        assert cache is not None
        # Should allow all paths
        directives = checker._find_matching_directives(cache.directives)
        assert directives is not None
        assert directives.is_allowed("/any/path")

    @patch.object(httpx.Client, "get")
    def test_fetch_robots_txt_timeout(self, mock_get: MagicMock) -> None:
        """Handle timeout when fetching robots.txt."""
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        checker = RobotsChecker()
        cache = checker.fetch_robots_txt("https://example.com")

        assert cache is None

    @patch.object(httpx.Client, "get")
    def test_is_allowed_uses_cache(self, mock_get: MagicMock) -> None:
        """is_allowed uses cached robots.txt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow: /admin/
"""
        mock_get.return_value = mock_response

        checker = RobotsChecker()

        # First call fetches
        result1 = checker.is_allowed("https://example.com/public")
        # Second call uses cache
        result2 = checker.is_allowed("https://example.com/admin/")

        assert result1 is True
        assert result2 is False
        # Should only fetch once
        assert mock_get.call_count == 1

    @patch.object(httpx.Client, "get")
    def test_is_allowed_allows_on_error(self, mock_get: MagicMock) -> None:
        """Allow access if robots.txt cannot be fetched."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        checker = RobotsChecker()
        result = checker.is_allowed("https://example.com/any/path")

        assert result is True

    @patch.object(httpx.Client, "get")
    def test_get_crawl_delay(self, mock_get: MagicMock) -> None:
        """Get crawl delay from robots.txt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Crawl-delay: 10
"""
        mock_get.return_value = mock_response

        checker = RobotsChecker()
        delay = checker.get_crawl_delay("https://example.com")

        assert delay == 10.0

    def test_clear_cache(self) -> None:
        """Clear cache removes all entries."""
        checker = RobotsChecker()
        # Manually add cache entry
        from datetime import UTC, datetime

        checker.cache["https://example.com"] = RobotsCache(
            content="",
            fetched_at=datetime.now(UTC),
            expires_at=datetime.now(UTC),
            directives=[],
        )

        checker.clear_cache()

        assert len(checker.cache) == 0

    def test_context_manager(self) -> None:
        """Checker works as context manager."""
        with RobotsChecker() as checker:
            assert checker is not None


class TestCreateRobotsChecker:
    """Tests for create_robots_checker factory function."""

    def test_default_values(self) -> None:
        """Factory creates checker with defaults."""
        checker = create_robots_checker()

        assert checker.user_agent == "OpenClawMonitor"
        assert checker.cache_duration == timedelta(hours=24)

    def test_custom_values(self) -> None:
        """Factory accepts custom values."""
        checker = create_robots_checker(
            user_agent="CustomBot",
            cache_hours=12.0,
        )

        assert checker.user_agent == "CustomBot"
        assert checker.cache_duration == timedelta(hours=12)
