"""Tests for the Moltbook API client."""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from monitor.api_client import (
    Agent,
    APIResponse,
    Comment,
    CommentSort,
    MoltbookClient,
    Post,
    PostSort,
    RateLimitInfo,
    Submolt,
)


class TestRateLimitInfo:
    """Tests for RateLimitInfo parsing."""

    def test_from_headers_all_present(self) -> None:
        """Parse rate limit info when all headers are present."""
        headers = httpx.Headers(
            {
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "42",
                "X-RateLimit-Reset": "1700000000",
            }
        )
        info = RateLimitInfo.from_headers(headers)

        assert info.limit == 100
        assert info.remaining == 42
        assert info.reset is not None
        assert info.reset.year == 2023

    def test_from_headers_none_present(self) -> None:
        """Parse rate limit info when no headers are present."""
        headers = httpx.Headers({})
        info = RateLimitInfo.from_headers(headers)

        assert info.limit is None
        assert info.remaining is None
        assert info.reset is None


class TestPost:
    """Tests for Post data model."""

    def test_from_api_response_basic(self) -> None:
        """Parse a basic post from API response."""
        data = {
            "id": "abc123",
            "title": "Test Post",
            "content": "Post content",
            "submolt": "test",
            "agent_id": "agent1",
            "score": 42,
            "created_at": "2024-01-15T10:30:00Z",
            "comment_count": 5,
        }
        post = Post.from_api_response(data)

        assert post.id == "abc123"
        assert post.title == "Test Post"
        assert post.content == "Post content"
        assert post.submolt == "test"
        assert post.agent_id == "agent1"
        assert post.score == 42
        assert post.comment_count == 5

    def test_from_api_response_unix_timestamp(self) -> None:
        """Parse post with Unix timestamp."""
        data = {
            "id": "abc123",
            "title": "Test Post",
            "submolt": "test",
            "agent_id": "agent1",
            "score": 0,
            "created_at": 1705315800,  # Unix timestamp
        }
        post = Post.from_api_response(data)

        assert post.id == "abc123"
        assert post.created_at.year == 2024

    def test_from_api_response_alternative_fields(self) -> None:
        """Parse post with alternative field names."""
        data = {
            "id": "abc123",
            "title": "Test Post",
            "submolt": "test",
            "author_id": "agent1",  # Alternative to agent_id
            "score": 0,
            "num_comments": 10,  # Alternative to comment_count
        }
        post = Post.from_api_response(data)

        assert post.agent_id == "agent1"
        assert post.comment_count == 10


class TestComment:
    """Tests for Comment data model."""

    def test_from_api_response_basic(self) -> None:
        """Parse a basic comment from API response."""
        data = {
            "id": "comment1",
            "parent_id": None,
            "content": "Comment text",
            "agent_id": "agent1",
            "score": 5,
            "created_at": "2024-01-15T10:30:00Z",
        }
        comment = Comment.from_api_response(data, post_id="post123")

        assert comment.id == "comment1"
        assert comment.post_id == "post123"
        assert comment.parent_id is None
        assert comment.content == "Comment text"
        assert comment.agent_id == "agent1"
        assert comment.score == 5

    def test_from_api_response_with_parent(self) -> None:
        """Parse a reply comment."""
        data = {
            "id": "comment2",
            "parent_id": "comment1",
            "body": "Reply text",  # Alternative field name
            "author_id": "agent2",
            "score": 3,
            "created_at": "2024-01-15T11:00:00Z",
        }
        comment = Comment.from_api_response(data, post_id="post123")

        assert comment.parent_id == "comment1"
        assert comment.content == "Reply text"
        assert comment.agent_id == "agent2"


class TestAgent:
    """Tests for Agent data model."""

    def test_from_api_response_basic(self) -> None:
        """Parse a basic agent profile."""
        data = {
            "id": "agent1",
            "name": "TestAgent",
            "description": "A test agent",
            "karma": 1000,
            "created_at": "2023-06-01T00:00:00Z",
        }
        agent = Agent.from_api_response(data)

        assert agent.id == "agent1"
        assert agent.name == "TestAgent"
        assert agent.description == "A test agent"
        assert agent.karma == 1000

    def test_from_api_response_alternative_fields(self) -> None:
        """Parse agent with alternative field names."""
        data = {
            "name": "TestAgent",
            "username": "TestAgent",
            "bio": "Agent bio",
            "total_karma": 500,
            "created_at": "2023-06-01T00:00:00Z",
        }
        agent = Agent.from_api_response(data)

        assert agent.name == "TestAgent"
        assert agent.description == "Agent bio"
        assert agent.karma == 500


class TestSubmolt:
    """Tests for Submolt data model."""

    def test_from_api_response_basic(self) -> None:
        """Parse a basic submolt."""
        data = {
            "name": "test",
            "display_name": "Test Community",
            "description": "A test submolt",
            "subscriber_count": 1000,
            "created_at": "2023-01-01T00:00:00Z",
        }
        submolt = Submolt.from_api_response(data)

        assert submolt.name == "test"
        assert submolt.display_name == "Test Community"
        assert submolt.description == "A test submolt"
        assert submolt.subscriber_count == 1000


class TestMoltbookClient:
    """Tests for MoltbookClient."""

    def test_init_defaults(self) -> None:
        """Client initializes with default values."""
        client = MoltbookClient()

        assert client.api_host == "www.moltbook.com"
        assert client.api_version == "v1"
        assert "OpenClawMonitor" in client.user_agent

    def test_init_custom_values(self) -> None:
        """Client accepts custom configuration."""
        client = MoltbookClient(
            proxy_base_url="http://custom-proxy:8080",
            timeout=60.0,
        )

        assert client.proxy_base_url == "http://custom-proxy:8080"
        assert client.timeout == 60.0

    def test_build_url(self) -> None:
        """URL building routes through proxy correctly."""
        client = MoltbookClient(proxy_base_url="http://proxy:8080")

        url = client._build_url("posts")
        assert url == "http://proxy:8080/proxy/www.moltbook.com/api/v1/posts"

        url = client._build_url("/posts/123")
        assert url == "http://proxy:8080/proxy/www.moltbook.com/api/v1/posts/123"

    def test_context_manager(self) -> None:
        """Client works as context manager."""
        with MoltbookClient() as client:
            assert client is not None

    @patch.object(httpx.Client, "get")
    def test_get_posts_success(self, mock_get: MagicMock) -> None:
        """Successful posts fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "post1",
                "title": "Test",
                "submolt": "test",
                "agent_id": "agent1",
                "score": 0,
                "created_at": "2024-01-15T00:00:00Z",
            }
        ]
        mock_response.headers = httpx.Headers({"X-RateLimit-Remaining": "99"})
        mock_get.return_value = mock_response

        with MoltbookClient() as client:
            response = client.get_posts(sort=PostSort.NEW)

        assert response.success
        assert response.status_code == 200
        assert len(response.data) == 1

    @patch.object(httpx.Client, "get")
    def test_get_posts_rate_limited(self, mock_get: MagicMock) -> None:
        """Handle rate limiting response."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "Rate limited"}
        mock_response.headers = httpx.Headers(
            {"X-RateLimit-Remaining": "0", "Retry-After": "60"}
        )
        mock_get.return_value = mock_response

        with MoltbookClient() as client:
            response = client.get_posts()

        assert not response.success
        assert response.status_code == 429
        assert response.rate_limit.remaining == 0

    @patch.object(httpx.Client, "get")
    def test_get_posts_timeout(self, mock_get: MagicMock) -> None:
        """Handle request timeout."""
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with MoltbookClient() as client:
            response = client.get_posts()

        assert not response.success
        assert response.status_code == 0
        assert "timeout" in response.error_message.lower()

    @patch.object(httpx.Client, "get")
    def test_get_posts_connection_error(self, mock_get: MagicMock) -> None:
        """Handle connection error."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with MoltbookClient() as client:
            response = client.get_posts()

        assert not response.success
        assert response.status_code == 0
        assert "connection" in response.error_message.lower()

    @patch.object(httpx.Client, "get")
    def test_fetch_posts_parses_response(self, mock_get: MagicMock) -> None:
        """fetch_posts returns parsed Post objects."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "posts": [
                {
                    "id": "post1",
                    "title": "Test Post",
                    "submolt": "test",
                    "agent_id": "agent1",
                    "score": 10,
                    "created_at": "2024-01-15T00:00:00Z",
                }
            ]
        }
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        with MoltbookClient() as client:
            posts, response = client.fetch_posts()

        assert len(posts) == 1
        assert isinstance(posts[0], Post)
        assert posts[0].id == "post1"
        assert posts[0].title == "Test Post"

    @patch.object(httpx.Client, "get")
    def test_get_comments(self, mock_get: MagicMock) -> None:
        """Fetch comments for a post."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": "comment1",
                "content": "Test comment",
                "agent_id": "agent1",
                "score": 5,
                "created_at": "2024-01-15T00:00:00Z",
            }
        ]
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        with MoltbookClient() as client:
            response = client.get_comments(
                post_id="post1", sort=CommentSort.TOP, limit=10
            )

        assert response.success
        mock_get.assert_called_once()
        # Verify params were passed
        call_args = mock_get.call_args
        assert "sort" in str(call_args) or call_args[1].get("params", {}).get("sort")

    @patch.object(httpx.Client, "get")
    def test_get_submolts(self, mock_get: MagicMock) -> None:
        """Fetch list of submolts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "name": "test",
                "display_name": "Test",
                "subscriber_count": 100,
                "created_at": "2024-01-01T00:00:00Z",
            }
        ]
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        with MoltbookClient() as client:
            response = client.get_submolts()

        assert response.success

    @patch.object(httpx.Client, "get")
    def test_get_agent_profile(self, mock_get: MagicMock) -> None:
        """Fetch agent profile."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "TestAgent",
            "karma": 1000,
            "created_at": "2023-01-01T00:00:00Z",
        }
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        with MoltbookClient() as client:
            response = client.get_agent_profile(name="TestAgent")

        assert response.success

    @patch.object(httpx.Client, "get")
    def test_search(self, mock_get: MagicMock) -> None:
        """Search for posts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.headers = httpx.Headers({})
        mock_get.return_value = mock_response

        with MoltbookClient() as client:
            response = client.search(query="test query", limit=10)

        assert response.success
        call_args = mock_get.call_args
        # Verify search params
        params = call_args[1].get("params", {})
        assert params.get("q") == "test query"
        assert params.get("limit") == 10
