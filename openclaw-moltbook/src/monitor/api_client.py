"""Moltbook API client for read-only access to the platform.

This module provides a client for interacting with the Moltbook API through
the reverse proxy. All requests are routed through the proxy for security
and rate limiting.

Key features:
- Read-only operations only (GET requests)
- Automatic routing through reverse proxy
- Rate limit header tracking
- Configurable User-Agent
- Support for all public Moltbook API endpoints
"""

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx


class PostSort(str, Enum):
    """Sort options for posts endpoint."""

    NEW = "new"
    HOT = "hot"
    TOP = "top"
    RISING = "rising"


class CommentSort(str, Enum):
    """Sort options for comments endpoint."""

    TOP = "top"
    NEW = "new"
    CONTROVERSIAL = "controversial"


@dataclass
class RateLimitInfo:
    """Rate limit information from API response headers."""

    limit: int | None = None
    remaining: int | None = None
    reset: datetime | None = None

    @classmethod
    def from_headers(cls, headers: httpx.Headers) -> "RateLimitInfo":
        """Parse rate limit info from response headers."""
        limit = headers.get("X-RateLimit-Limit")
        remaining = headers.get("X-RateLimit-Remaining")
        reset = headers.get("X-RateLimit-Reset")

        return cls(
            limit=int(limit) if limit else None,
            remaining=int(remaining) if remaining else None,
            reset=datetime.fromtimestamp(float(reset), tz=UTC) if reset else None,
        )


@dataclass
class Post:
    """Moltbook post data model."""

    id: str
    title: str
    content: str | None
    url: str | None
    submolt: str
    agent_id: str
    score: int
    created_at: datetime
    comment_count: int = 0

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Post":
        """Create Post from API response data."""
        # Handle timestamps - API may return ISO format or Unix timestamp
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            # ISO format
            created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, int | float):
            # Unix timestamp
            created_at_dt = datetime.fromtimestamp(created_at, tz=UTC)
        else:
            created_at_dt = datetime.now(UTC)

        return cls(
            id=str(data.get("id", "")),
            title=data.get("title", ""),
            content=data.get("content"),
            url=data.get("url"),
            submolt=data.get("submolt", ""),
            agent_id=str(data.get("agent_id", data.get("author_id", ""))),
            score=data.get("score", 0),
            created_at=created_at_dt,
            comment_count=data.get("comment_count", data.get("num_comments", 0)),
        )


@dataclass
class Comment:
    """Moltbook comment data model."""

    id: str
    post_id: str
    parent_id: str | None
    content: str
    agent_id: str
    score: int
    created_at: datetime

    @classmethod
    def from_api_response(cls, data: dict[str, Any], post_id: str) -> "Comment":
        """Create Comment from API response data."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, int | float):
            created_at_dt = datetime.fromtimestamp(created_at, tz=UTC)
        else:
            created_at_dt = datetime.now(UTC)

        return cls(
            id=str(data.get("id", "")),
            post_id=post_id,
            parent_id=str(data.get("parent_id")) if data.get("parent_id") else None,
            content=data.get("content", data.get("body", "")),
            agent_id=str(data.get("agent_id", data.get("author_id", ""))),
            score=data.get("score", 0),
            created_at=created_at_dt,
        )


@dataclass
class Agent:
    """Moltbook agent (user) profile data model."""

    id: str
    name: str
    description: str | None
    karma: int
    created_at: datetime

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Agent":
        """Create Agent from API response data."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, int | float):
            created_at_dt = datetime.fromtimestamp(created_at, tz=UTC)
        else:
            created_at_dt = datetime.now(UTC)

        return cls(
            id=str(data.get("id", data.get("name", ""))),
            name=data.get("name", data.get("username", "")),
            description=data.get("description", data.get("bio")),
            karma=data.get("karma", data.get("total_karma", 0)),
            created_at=created_at_dt,
        )


@dataclass
class Submolt:
    """Moltbook community (submolt) data model."""

    name: str
    display_name: str
    description: str | None
    subscriber_count: int
    created_at: datetime

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "Submolt":
        """Create Submolt from API response data."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, int | float):
            created_at_dt = datetime.fromtimestamp(created_at, tz=UTC)
        else:
            created_at_dt = datetime.now(UTC)

        return cls(
            name=data.get("name", ""),
            display_name=data.get("display_name", data.get("title", "")),
            description=data.get("description"),
            subscriber_count=data.get("subscriber_count", data.get("subscribers", 0)),
            created_at=created_at_dt,
        )


@dataclass
class APIResponse:
    """Wrapper for API responses with rate limit info."""

    data: Any
    rate_limit: RateLimitInfo
    status_code: int
    success: bool
    error_message: str | None = None


@dataclass
class MoltbookClient:
    """Read-only client for the Moltbook API.

    All requests are routed through the reverse proxy for security.
    Tracks rate limit information from response headers.

    Attributes:
        proxy_base_url: Base URL of the reverse proxy
        api_base_url: Base URL of the Moltbook API (for path construction)
        user_agent: User-Agent header for requests
        timeout: Request timeout in seconds
        last_rate_limit: Most recent rate limit info from API
    """

    proxy_base_url: str = field(
        default_factory=lambda: os.getenv("PROXY_URL", "http://proxy:8080")
    )
    api_host: str = "www.moltbook.com"
    api_version: str = "v1"
    user_agent: str = "OpenClawMonitor/1.0 (research purposes)"
    timeout: float = 30.0
    last_rate_limit: RateLimitInfo = field(default_factory=RateLimitInfo)
    _client: httpx.Client | None = field(default=None, repr=False)

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "MoltbookClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def _build_url(self, path: str) -> str:
        """Build full URL routing through proxy.

        The proxy expects URLs in format: /proxy/{host}/{path}
        """
        # Remove leading slash if present
        path = path.lstrip("/")
        return f"{self.proxy_base_url}/proxy/{self.api_host}/api/{self.api_version}/{path}"

    def _request(self, path: str, params: dict[str, Any] | None = None) -> APIResponse:
        """Make a GET request through the proxy.

        Args:
            path: API path (e.g., "posts")
            params: Query parameters

        Returns:
            APIResponse with data and rate limit info
        """
        url = self._build_url(path)
        client = self._get_client()

        try:
            response = client.get(url, params=params)

            # Update rate limit info
            self.last_rate_limit = RateLimitInfo.from_headers(response.headers)

            if response.status_code == 200:
                return APIResponse(
                    data=response.json(),
                    rate_limit=self.last_rate_limit,
                    status_code=response.status_code,
                    success=True,
                )
            else:
                error_msg = f"API returned status {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                    elif "message" in error_data:
                        error_msg = error_data["message"]
                except Exception:
                    error_msg = response.text[:200] if response.text else error_msg

                return APIResponse(
                    data=None,
                    rate_limit=self.last_rate_limit,
                    status_code=response.status_code,
                    success=False,
                    error_message=error_msg,
                )

        except httpx.TimeoutException as e:
            return APIResponse(
                data=None,
                rate_limit=self.last_rate_limit,
                status_code=0,
                success=False,
                error_message=f"Request timeout: {e}",
            )
        except httpx.ConnectError as e:
            return APIResponse(
                data=None,
                rate_limit=self.last_rate_limit,
                status_code=0,
                success=False,
                error_message=f"Connection error: {e}",
            )
        except Exception as e:
            return APIResponse(
                data=None,
                rate_limit=self.last_rate_limit,
                status_code=0,
                success=False,
                error_message=f"Request error: {e}",
            )

    def get_posts(
        self,
        sort: PostSort = PostSort.NEW,
        limit: int = 25,
        after: str | None = None,
    ) -> APIResponse:
        """Fetch posts from Moltbook.

        Args:
            sort: Sort order (new, hot, top, rising)
            limit: Number of posts to fetch (max 25)
            after: Pagination cursor (post ID to start after)

        Returns:
            APIResponse with list of post data
        """
        params: dict[str, Any] = {
            "sort": sort.value,
            "limit": min(limit, 25),
        }
        if after:
            params["after"] = after

        return self._request("posts", params)

    def get_post(self, post_id: str) -> APIResponse:
        """Fetch a single post by ID.

        Args:
            post_id: The post ID to fetch

        Returns:
            APIResponse with post data
        """
        return self._request(f"posts/{post_id}")

    def get_comments(
        self,
        post_id: str,
        sort: CommentSort = CommentSort.TOP,
        limit: int = 25,
    ) -> APIResponse:
        """Fetch comments for a post.

        Args:
            post_id: The post ID to get comments for
            sort: Sort order (top, new, controversial)
            limit: Number of comments to fetch

        Returns:
            APIResponse with list of comment data
        """
        params: dict[str, Any] = {
            "sort": sort.value,
            "limit": min(limit, 100),
        }
        return self._request(f"posts/{post_id}/comments", params)

    def get_submolts(self) -> APIResponse:
        """Fetch list of all submolts (communities).

        Returns:
            APIResponse with list of submolt data
        """
        return self._request("submolts")

    def get_submolt(self, name: str) -> APIResponse:
        """Fetch details for a specific submolt.

        Args:
            name: The submolt name

        Returns:
            APIResponse with submolt data
        """
        return self._request(f"submolts/{name}")

    def get_agent_profile(self, name: str) -> APIResponse:
        """Fetch an agent's profile.

        Args:
            name: The agent (user) name

        Returns:
            APIResponse with agent profile data
        """
        return self._request("agents/profile", params={"name": name})

    def search(self, query: str, limit: int = 25) -> APIResponse:
        """Search for posts.

        Args:
            query: Search query string
            limit: Number of results to return

        Returns:
            APIResponse with search results
        """
        params: dict[str, Any] = {
            "q": query,
            "limit": min(limit, 25),
        }
        return self._request("search", params)

    # Convenience methods that parse responses into typed objects

    def fetch_posts(
        self,
        sort: PostSort = PostSort.NEW,
        limit: int = 25,
        after: str | None = None,
    ) -> tuple[list[Post], APIResponse]:
        """Fetch and parse posts into Post objects.

        Returns:
            Tuple of (list of Post objects, raw APIResponse)
        """
        response = self.get_posts(sort=sort, limit=limit, after=after)
        posts: list[Post] = []

        if response.success and response.data:
            # Handle both list and dict with 'posts' key
            post_list = (
                response.data
                if isinstance(response.data, list)
                else response.data.get("posts", response.data.get("data", []))
            )
            for post_data in post_list:
                try:
                    posts.append(Post.from_api_response(post_data))
                except Exception:
                    # Skip malformed posts
                    continue

        return posts, response

    def fetch_post(self, post_id: str) -> tuple[Post | None, APIResponse]:
        """Fetch and parse a single post.

        Returns:
            Tuple of (Post object or None, raw APIResponse)
        """
        response = self.get_post(post_id)

        if response.success and response.data:
            try:
                post_data = (
                    response.data
                    if "id" in response.data
                    else response.data.get("post", response.data.get("data", {}))
                )
                return Post.from_api_response(post_data), response
            except Exception:
                return None, response

        return None, response

    def fetch_comments(
        self,
        post_id: str,
        sort: CommentSort = CommentSort.TOP,
        limit: int = 25,
    ) -> tuple[list[Comment], APIResponse]:
        """Fetch and parse comments for a post.

        Returns:
            Tuple of (list of Comment objects, raw APIResponse)
        """
        response = self.get_comments(post_id=post_id, sort=sort, limit=limit)
        comments: list[Comment] = []

        if response.success and response.data:
            comment_list = (
                response.data
                if isinstance(response.data, list)
                else response.data.get("comments", response.data.get("data", []))
            )
            for comment_data in comment_list:
                try:
                    comments.append(Comment.from_api_response(comment_data, post_id))
                except Exception:
                    continue

        return comments, response

    def fetch_submolts(self) -> tuple[list[Submolt], APIResponse]:
        """Fetch and parse all submolts.

        Returns:
            Tuple of (list of Submolt objects, raw APIResponse)
        """
        response = self.get_submolts()
        submolts: list[Submolt] = []

        if response.success and response.data:
            submolt_list = (
                response.data
                if isinstance(response.data, list)
                else response.data.get("submolts", response.data.get("data", []))
            )
            for submolt_data in submolt_list:
                try:
                    submolts.append(Submolt.from_api_response(submolt_data))
                except Exception:
                    continue

        return submolts, response

    def fetch_agent(self, name: str) -> tuple[Agent | None, APIResponse]:
        """Fetch and parse an agent profile.

        Returns:
            Tuple of (Agent object or None, raw APIResponse)
        """
        response = self.get_agent_profile(name)

        if response.success and response.data:
            try:
                agent_data = (
                    response.data
                    if "name" in response.data
                    else response.data.get("agent", response.data.get("data", {}))
                )
                return Agent.from_api_response(agent_data), response
            except Exception:
                return None, response

        return None, response
