"""Tests for FastAPI web application.

Tests cover:
- Health endpoints
- API responses
- CORS and middleware
- Admin auth endpoints
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from monitor.admin_auth import hash_password, save_password_hash
from monitor.web import app

client = TestClient(app, raise_server_exceptions=True)


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


class TestAdminEndpoints:
    """Tests for /admin/* endpoints."""

    def _creds_env(self, tmp_path: Path) -> dict[str, str]:
        return {"ADMIN_CREDS_PATH": str(tmp_path / "admin.creds"), "ADMIN_PASSWORD_HASH": ""}

    def test_status_requires_auth(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, self._creds_env(tmp_path)):
            save_password_hash(hash_password("pass1234"))
            response = client.get("/admin/status")
        assert response.status_code == 401

    def test_status_rejects_wrong_credentials(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, self._creds_env(tmp_path)):
            save_password_hash(hash_password("correct"))
            response = client.get("/admin/status", auth=("admin", "wrong"))
        assert response.status_code == 401

    def test_status_accepts_correct_credentials(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, self._creds_env(tmp_path)):
            save_password_hash(hash_password("correct"))
            response = client.get("/admin/status", auth=("admin", "correct"))
        assert response.status_code == 200
        assert response.json()["authenticated"] is True

    def test_change_password_rejects_unauthenticated(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, self._creds_env(tmp_path)):
            save_password_hash(hash_password("original"))
            response = client.post(
                "/admin/change-password", json={"new_password": "newpass1234"}
            )
        assert response.status_code == 401

    def test_change_password_succeeds_and_new_password_works(self, tmp_path: Path) -> None:
        env = self._creds_env(tmp_path)
        with patch.dict(os.environ, env):
            save_password_hash(hash_password("original"))
            r = client.post(
                "/admin/change-password",
                json={"new_password": "brandnew99"},
                auth=("admin", "original"),
            )
            assert r.status_code == 204
            # old password no longer works
            r2 = client.get("/admin/status", auth=("admin", "original"))
            assert r2.status_code == 401
            # new password works
            r3 = client.get("/admin/status", auth=("admin", "brandnew99"))
            assert r3.status_code == 200

    def test_change_password_rejects_short_password(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, self._creds_env(tmp_path)):
            save_password_hash(hash_password("original"))
            r = client.post(
                "/admin/change-password",
                json={"new_password": "short"},
                auth=("admin", "original"),
            )
        assert r.status_code == 400


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
