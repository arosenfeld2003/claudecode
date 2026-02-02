"""Pytest configuration and shared fixtures."""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database path for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_monitor.duckdb"
        yield db_path


@pytest.fixture
def mock_proxy_url() -> str:
    """Return mock proxy URL for testing."""
    return "http://localhost:8080/health"


@pytest.fixture(autouse=True)
def set_test_env(temp_db_path: Path) -> Generator[None, None, None]:
    """Set environment variables for testing."""
    original_db_path = os.environ.get("MONITOR_DB_PATH")
    original_proxy_url = os.environ.get("PROXY_HEALTH_URL")

    os.environ["MONITOR_DB_PATH"] = str(temp_db_path)
    os.environ["PROXY_HEALTH_URL"] = "http://localhost:8080/health"

    yield

    # Restore original values
    if original_db_path:
        os.environ["MONITOR_DB_PATH"] = original_db_path
    elif "MONITOR_DB_PATH" in os.environ:
        del os.environ["MONITOR_DB_PATH"]

    if original_proxy_url:
        os.environ["PROXY_HEALTH_URL"] = original_proxy_url
    elif "PROXY_HEALTH_URL" in os.environ:
        del os.environ["PROXY_HEALTH_URL"]
