"""robots.txt compliance module for Moltbook API.

Implements robots.txt parsing and compliance:
- Fetch robots.txt on startup
- Cache for 24 hours
- Honor Crawl-delay if specified
- Skip disallowed paths
- User-Agent matching

Reference: https://www.robotstxt.org/robotstxt.html
"""

import contextlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass
class RobotsRule:
    """A single rule from robots.txt."""

    path: str
    allow: bool

    def matches(self, path: str) -> bool:
        """Check if this rule matches the given path.

        Supports * wildcard and $ end anchor.
        """
        pattern = self.path

        # Escape regex special characters except * and $
        pattern = re.escape(pattern)

        # Convert * wildcard to regex
        pattern = pattern.replace(r"\*", ".*")

        # Handle $ end anchor - if ends with \$, replace with actual $, else prefix with ^
        pattern = pattern[:-2] + "$" if pattern.endswith(r"\$") else "^" + pattern

        try:
            return bool(re.match(pattern, path))
        except re.error:
            # If regex fails, try simple prefix match
            return path.startswith(self.path.rstrip("*$"))


@dataclass
class RobotsDirectives:
    """Parsed directives for a user-agent from robots.txt."""

    user_agent: str
    rules: list[RobotsRule] = field(default_factory=list)
    crawl_delay: float | None = None
    sitemaps: list[str] = field(default_factory=list)

    def is_allowed(self, path: str) -> bool:
        """Check if a path is allowed by these directives.

        Rules are processed in order; first match wins.
        If no rule matches, access is allowed by default.
        """
        for rule in self.rules:
            if rule.matches(path):
                return rule.allow
        # Default: allowed
        return True


@dataclass
class RobotsCache:
    """Cached robots.txt content with expiration."""

    content: str
    fetched_at: datetime
    expires_at: datetime
    directives: list[RobotsDirectives] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if the cache has expired."""
        return datetime.now(UTC) > self.expires_at


@dataclass
class RobotsChecker:
    """robots.txt compliance checker.

    Fetches, parses, and caches robots.txt files.
    Checks paths against robots.txt rules.

    Attributes:
        user_agent: User-Agent string to match against robots.txt
        cache_duration: How long to cache robots.txt (default: 24 hours)
        cache: Dict mapping base URLs to cached robots.txt data
    """

    user_agent: str = "OpenClawMonitor"
    cache_duration: timedelta = field(default_factory=lambda: timedelta(hours=24))
    cache: dict[str, RobotsCache] = field(default_factory=dict)
    _client: httpx.Client | None = field(default=None, repr=False)

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=10.0,
                headers={"User-Agent": f"{self.user_agent}/1.0 (research purposes)"},
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "RobotsChecker":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def _parse_robots_txt(self, content: str) -> list[RobotsDirectives]:
        """Parse robots.txt content into directives.

        Args:
            content: Raw robots.txt content

        Returns:
            List of RobotsDirectives for different user-agents
        """
        directives_list: list[RobotsDirectives] = []
        current_directives: RobotsDirectives | None = None
        sitemaps: list[str] = []

        for line in content.splitlines():
            # Remove comments and whitespace
            line = line.split("#", 1)[0].strip()
            if not line:
                continue

            # Parse key: value
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                # Start new directives block
                if current_directives is not None:
                    current_directives.sitemaps = sitemaps
                    directives_list.append(current_directives)
                current_directives = RobotsDirectives(user_agent=value)
            elif current_directives is not None:
                if key == "disallow":
                    if value:  # Empty disallow means allow all
                        current_directives.rules.append(
                            RobotsRule(path=value, allow=False)
                        )
                elif key == "allow":
                    if value:
                        current_directives.rules.append(
                            RobotsRule(path=value, allow=True)
                        )
                elif key == "crawl-delay":
                    with contextlib.suppress(ValueError):
                        current_directives.crawl_delay = float(value)
            if key == "sitemap":
                sitemaps.append(value)

        # Add last directives block
        if current_directives is not None:
            current_directives.sitemaps = sitemaps
            directives_list.append(current_directives)

        return directives_list

    def _find_matching_directives(
        self, directives_list: list[RobotsDirectives]
    ) -> RobotsDirectives | None:
        """Find the directives that match our user-agent.

        Matching priority:
        1. Exact match
        2. Partial match (user-agent contains our name)
        3. Wildcard (*)
        4. None if no match
        """
        exact_match: RobotsDirectives | None = None
        partial_match: RobotsDirectives | None = None
        wildcard_match: RobotsDirectives | None = None

        ua_lower = self.user_agent.lower()

        for directives in directives_list:
            agent = directives.user_agent.lower()

            if agent == ua_lower:
                exact_match = directives
            elif agent == "*":
                wildcard_match = directives
            elif agent in ua_lower or ua_lower in agent:
                partial_match = directives

        return exact_match or partial_match or wildcard_match

    def fetch_robots_txt(
        self, base_url: str, proxy_url: str | None = None
    ) -> RobotsCache | None:
        """Fetch and parse robots.txt for a domain.

        Args:
            base_url: Base URL of the site (e.g., https://www.moltbook.com)
            proxy_url: Optional proxy URL to route request through

        Returns:
            RobotsCache with parsed directives, or None on error
        """
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        # If proxy URL provided, route through it
        if proxy_url:
            host = parsed.netloc
            robots_url = f"{proxy_url}/proxy/{host}/robots.txt"

        client = self._get_client()

        try:
            response = client.get(robots_url)

            if response.status_code == 200:
                content = response.text
            elif response.status_code == 404:
                # No robots.txt means everything is allowed
                content = "User-agent: *\nAllow: /"
            else:
                logger.warning(
                    "Failed to fetch robots.txt from %s: status %d",
                    robots_url,
                    response.status_code,
                )
                # On error, assume everything is allowed
                content = "User-agent: *\nAllow: /"

            now = datetime.now(UTC)
            directives = self._parse_robots_txt(content)

            cache_entry = RobotsCache(
                content=content,
                fetched_at=now,
                expires_at=now + self.cache_duration,
                directives=directives,
            )

            # Store in cache
            cache_key = f"{parsed.scheme}://{parsed.netloc}"
            self.cache[cache_key] = cache_entry

            logger.info(
                "Fetched robots.txt from %s: %d directives",
                robots_url,
                len(directives),
            )

            return cache_entry

        except httpx.TimeoutException:
            logger.warning("Timeout fetching robots.txt from %s", robots_url)
            return None
        except httpx.ConnectError:
            logger.warning("Connection error fetching robots.txt from %s", robots_url)
            return None
        except Exception as e:
            logger.exception("Error fetching robots.txt from %s: %s", robots_url, e)
            return None

    def is_allowed(
        self,
        url: str,
        proxy_url: str | None = None,
        refresh: bool = False,
    ) -> bool:
        """Check if a URL is allowed by robots.txt.

        Args:
            url: Full URL to check
            proxy_url: Optional proxy URL for fetching robots.txt
            refresh: Force refresh of robots.txt cache

        Returns:
            True if the URL is allowed, False otherwise
        """
        parsed = urlparse(url)
        cache_key = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path or "/"

        # Check cache
        cache_entry = self.cache.get(cache_key)
        if cache_entry is None or cache_entry.is_expired() or refresh:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            cache_entry = self.fetch_robots_txt(base_url, proxy_url)

        if cache_entry is None:
            # On error fetching robots.txt, allow by default
            # This is the recommended behavior per robots.txt spec
            return True

        # Find matching directives
        directives = self._find_matching_directives(cache_entry.directives)
        if directives is None:
            # No matching user-agent, allow everything
            return True

        return directives.is_allowed(path)

    def get_crawl_delay(
        self,
        base_url: str,
        proxy_url: str | None = None,
    ) -> float | None:
        """Get the crawl delay for a domain.

        Args:
            base_url: Base URL of the site
            proxy_url: Optional proxy URL for fetching robots.txt

        Returns:
            Crawl delay in seconds, or None if not specified
        """
        parsed = urlparse(base_url)
        cache_key = f"{parsed.scheme}://{parsed.netloc}"

        # Check cache
        cache_entry = self.cache.get(cache_key)
        if cache_entry is None or cache_entry.is_expired():
            cache_entry = self.fetch_robots_txt(base_url, proxy_url)

        if cache_entry is None:
            return None

        # Find matching directives
        directives = self._find_matching_directives(cache_entry.directives)
        if directives is None:
            return None

        return directives.crawl_delay

    def get_sitemaps(
        self,
        base_url: str,
        proxy_url: str | None = None,
    ) -> list[str]:
        """Get sitemap URLs from robots.txt.

        Args:
            base_url: Base URL of the site
            proxy_url: Optional proxy URL for fetching robots.txt

        Returns:
            List of sitemap URLs
        """
        parsed = urlparse(base_url)
        cache_key = f"{parsed.scheme}://{parsed.netloc}"

        # Check cache
        cache_entry = self.cache.get(cache_key)
        if cache_entry is None or cache_entry.is_expired():
            cache_entry = self.fetch_robots_txt(base_url, proxy_url)

        if cache_entry is None:
            return []

        # Collect all sitemaps from all directives
        sitemaps: set[str] = set()
        for directives in cache_entry.directives:
            sitemaps.update(directives.sitemaps)

        return list(sitemaps)

    def clear_cache(self) -> None:
        """Clear all cached robots.txt data."""
        self.cache.clear()

    def get_cache_status(self) -> dict[str, Any]:
        """Get status of the robots.txt cache.

        Returns:
            Dict with cache entries and their status
        """
        now = datetime.now(UTC)
        return {
            "entries": {
                url: {
                    "fetched_at": entry.fetched_at.isoformat(),
                    "expires_at": entry.expires_at.isoformat(),
                    "is_expired": entry.is_expired(),
                    "time_until_expiry": (entry.expires_at - now).total_seconds(),
                    "directive_count": len(entry.directives),
                }
                for url, entry in self.cache.items()
            },
            "cache_duration_hours": self.cache_duration.total_seconds() / 3600,
        }


def create_robots_checker(
    user_agent: str = "OpenClawMonitor",
    cache_hours: float = 24.0,
) -> RobotsChecker:
    """Create a robots.txt checker with the specified config.

    Args:
        user_agent: User-Agent string for robots.txt matching
        cache_hours: How long to cache robots.txt (default: 24 hours)

    Returns:
        Configured RobotsChecker instance
    """
    return RobotsChecker(
        user_agent=user_agent,
        cache_duration=timedelta(hours=cache_hours),
    )
