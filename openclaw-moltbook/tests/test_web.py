"""Tests for FastAPI web application.

Tests cover:
- Health endpoints
- API responses
- CORS and middleware
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from monitor.web import app

client = TestClient(app)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self) -> None:
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "OpenClaw Moltbook Monitor"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_returns_200_when_healthy(self, temp_db_path: Path) -> None:
        """Test health endpoint returns 200 when system is healthy."""
        with patch("monitor.health.HealthChecker.check_proxy") as mock_proxy:
            mock_proxy.return_value = {"healthy": True, "message": "OK"}

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data

    def test_health_returns_503_when_unhealthy(self) -> None:
        """Test health endpoint returns 503 when system is unhealthy."""
        with patch("monitor.health.HealthChecker.check_database") as mock_db:
            mock_db.return_value = {"healthy": False, "message": "DB error"}

            with patch("monitor.health.HealthChecker.check_proxy") as mock_proxy:
                mock_proxy.return_value = {"healthy": False, "message": "Proxy error"}

                response = client.get("/health")

                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"


class TestDetailedHealthEndpoint:
    """Tests for detailed health API endpoint."""

    def test_detailed_health_returns_components(self, temp_db_path: Path) -> None:
        """Test detailed health endpoint returns component status."""
        with patch("monitor.health.HealthChecker.check_proxy") as mock_proxy:
            mock_proxy.return_value = {"healthy": True, "message": "OK"}

            response = client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data
            assert "components" in data
            assert "database" in data["components"]
            assert "proxy" in data["components"]

    def test_detailed_health_shows_unhealthy_components(self) -> None:
        """Test detailed health shows which components are unhealthy."""
        with patch("monitor.health.HealthChecker.check_database") as mock_db:
            mock_db.return_value = {"healthy": True, "message": "DB OK"}

            with patch("monitor.health.HealthChecker.check_proxy") as mock_proxy:
                mock_proxy.return_value = {"healthy": False, "message": "Proxy down"}

                response = client.get("/api/health")

                data = response.json()
                assert data["components"]["database"]["healthy"] is True
                assert data["components"]["proxy"]["healthy"] is False


class TestOpenAPIDocumentation:
    """Tests for OpenAPI documentation."""

    def test_openapi_schema_available(self) -> None:
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert data["info"]["title"] == "OpenClaw Moltbook Monitor"
        assert "paths" in data
        assert "/health" in data["paths"]

    def test_docs_endpoint_available(self) -> None:
        """Test Swagger UI docs endpoint is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
