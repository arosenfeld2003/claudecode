"""Tests for health check functionality.

Tests cover:
- Database connectivity checks
- Proxy connectivity checks
- Overall health status
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from monitor.health import HealthChecker


class TestHealthChecker:
    """Tests for HealthChecker class."""

    def test_init_default_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization with default paths."""
        # Remove env vars to test defaults
        monkeypatch.delenv("MONITOR_DB_PATH", raising=False)
        monkeypatch.delenv("PROXY_HEALTH_URL", raising=False)

        checker = HealthChecker()
        assert checker.db_path == Path("/app/data/monitor.duckdb")
        assert checker.proxy_url == "http://proxy:8080/health"

    def test_init_custom_paths(self) -> None:
        """Test initialization with custom paths."""
        checker = HealthChecker(
            db_path="/custom/path/db.duckdb",
            proxy_url="http://custom:9090/health",
        )
        assert checker.db_path == Path("/custom/path/db.duckdb")
        assert checker.proxy_url == "http://custom:9090/health"


class TestDatabaseHealth:
    """Tests for database health checks."""

    def test_database_healthy(self, temp_db_path: Path) -> None:
        """Test database health check when database is accessible."""
        checker = HealthChecker(db_path=str(temp_db_path))
        result = checker.check_database()

        assert result["healthy"] is True
        assert "Connected to" in result["message"]

    def test_database_directory_missing(self) -> None:
        """Test database health check when directory doesn't exist."""
        checker = HealthChecker(db_path="/nonexistent/path/db.duckdb")
        result = checker.check_database()

        assert result["healthy"] is False
        assert "does not exist" in result["message"]

    def test_database_connection_error(self) -> None:
        """Test database health check when database path is invalid."""
        # Use a path where the directory doesn't exist
        checker = HealthChecker(db_path="/nonexistent/subdir/test.duckdb")
        result = checker.check_database()

        # Should handle the error gracefully
        assert result["healthy"] is False
        assert "does not exist" in result["message"]


class TestProxyHealth:
    """Tests for proxy health checks."""

    def test_proxy_healthy(self) -> None:
        """Test proxy health check when proxy is reachable."""
        checker = HealthChecker(proxy_url="http://test:8080/health")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.05

        with patch.object(httpx.Client, "get", return_value=mock_response):
            result = checker.check_proxy()

        assert result["healthy"] is True
        assert "reachable" in result["message"]
        assert result["response_time_ms"] == 50.0

    def test_proxy_unhealthy_status(self) -> None:
        """Test proxy health check when proxy returns error status."""
        checker = HealthChecker(proxy_url="http://test:8080/health")

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch.object(httpx.Client, "get", return_value=mock_response):
            result = checker.check_proxy()

        assert result["healthy"] is False
        assert "503" in result["message"]

    def test_proxy_connection_refused(self) -> None:
        """Test proxy health check when connection is refused."""
        checker = HealthChecker(proxy_url="http://test:8080/health")

        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("Connection refused")):
            result = checker.check_proxy()

        assert result["healthy"] is False
        assert "connection refused" in result["message"].lower()

    def test_proxy_timeout(self) -> None:
        """Test proxy health check when connection times out."""
        checker = HealthChecker(proxy_url="http://test:8080/health")

        with patch.object(httpx.Client, "get", side_effect=httpx.TimeoutException("Timeout")):
            result = checker.check_proxy()

        assert result["healthy"] is False
        assert "timed out" in result["message"]


class TestOverallHealth:
    """Tests for overall health status."""

    def test_check_all_returns_all_components(self, temp_db_path: Path) -> None:
        """Test that check_all returns status for all components."""
        checker = HealthChecker(
            db_path=str(temp_db_path),
            proxy_url="http://test:8080/health",
        )

        # Mock proxy as healthy
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.01

        with patch.object(httpx.Client, "get", return_value=mock_response):
            result = checker.check_all()

        assert "timestamp" in result
        assert "healthy" in result
        assert "database" in result
        assert "proxy" in result

    def test_check_all_healthy_when_db_healthy(self, temp_db_path: Path) -> None:
        """Test that overall health is true when database is healthy."""
        checker = HealthChecker(
            db_path=str(temp_db_path),
            proxy_url="http://test:8080/health",
        )

        # Proxy may fail but overall health depends on database
        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("No proxy")):
            result = checker.check_all()

        # Overall health is based on database
        assert result["healthy"] is True
        assert result["database"]["healthy"] is True
        assert result["proxy"]["healthy"] is False

    def test_to_json_response_format(self, temp_db_path: Path) -> None:
        """Test JSON response format for HTTP endpoint."""
        checker = HealthChecker(
            db_path=str(temp_db_path),
            proxy_url="http://test:8080/health",
        )

        with patch.object(httpx.Client, "get", side_effect=httpx.ConnectError("No proxy")):
            result = checker.to_json_response()

        assert "status" in result
        assert "timestamp" in result
        assert "components" in result
        assert "database" in result["components"]
        assert "proxy" in result["components"]
