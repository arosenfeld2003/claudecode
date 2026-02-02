"""Tests for CLI commands.

Tests cover:
- Command parsing and options
- Output formats (text/json)
- Health command functionality
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from typer.testing import CliRunner

from monitor.cli import app

runner = CliRunner()


class TestCLIBasics:
    """Tests for basic CLI functionality."""

    def test_cli_help(self) -> None:
        """Test that CLI shows help without args."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "OpenClaw Moltbook Monitor" in result.stdout

    def test_version_command(self) -> None:
        """Test version command shows version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout

    def test_verbose_option(self) -> None:
        """Test verbose option is accepted."""
        result = runner.invoke(app, ["--verbose", "version"])
        assert result.exit_code == 0
        assert "Verbose mode enabled" in result.stdout


class TestHealthCommand:
    """Tests for health command."""

    def test_health_text_output(self, temp_db_path: Path) -> None:
        """Test health command with text output."""
        with patch("monitor.health.HealthChecker.check_proxy") as mock_proxy:
            mock_proxy.return_value = {"healthy": True, "message": "Proxy OK"}

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "Health Status" in result.stdout

    def test_health_json_output(self, temp_db_path: Path) -> None:
        """Test health command with JSON output."""
        with patch("monitor.health.HealthChecker.check_proxy") as mock_proxy:
            mock_proxy.return_value = {"healthy": True, "message": "Proxy OK"}

            result = runner.invoke(app, ["health", "--format", "json"])

            assert result.exit_code == 0
            assert '"timestamp"' in result.stdout
            assert '"database"' in result.stdout

    def test_health_unhealthy_exit_code(self) -> None:
        """Test health command returns exit code 1 when unhealthy."""
        with patch("monitor.health.HealthChecker.check_database") as mock_db:
            mock_db.return_value = {"healthy": False, "message": "DB error"}

            with patch("monitor.health.HealthChecker.check_proxy") as mock_proxy:
                mock_proxy.return_value = {"healthy": False, "message": "Proxy error"}

                result = runner.invoke(app, ["health"])

                assert result.exit_code == 1


class TestStatusCommand:
    """Tests for status command (placeholder)."""

    def test_status_shows_not_implemented(self) -> None:
        """Test status command shows not implemented message."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "not yet fully implemented" in result.stdout.lower()

    def test_status_json_format(self) -> None:
        """Test status command with JSON format."""
        result = runner.invoke(app, ["status", "--format", "json"])
        assert result.exit_code == 0
        assert '"status"' in result.stdout


class TestStreamCommand:
    """Tests for stream command (placeholder)."""

    def test_stream_shows_not_implemented(self) -> None:
        """Test stream command shows not implemented message."""
        result = runner.invoke(app, ["stream"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout.lower()

    def test_stream_with_filters(self) -> None:
        """Test stream command accepts filter options."""
        result = runner.invoke(
            app, ["stream", "--submolt", "test", "--theme", "emerging_tech", "--goal", "trends"]
        )
        assert result.exit_code == 0
        assert "test" in result.stdout
        assert "emerging_tech" in result.stdout
        assert "trends" in result.stdout


class TestThemesCommand:
    """Tests for themes command (placeholder)."""

    def test_themes_shows_not_implemented(self) -> None:
        """Test themes command shows not implemented message."""
        result = runner.invoke(app, ["themes"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout.lower()

    def test_themes_evolve_option(self) -> None:
        """Test themes command with --evolve flag."""
        result = runner.invoke(app, ["themes", "--evolve"])
        assert result.exit_code == 0
        assert "evolution" in result.stdout.lower()


class TestTrendsCommand:
    """Tests for trends command (placeholder)."""

    def test_trends_shows_not_implemented(self) -> None:
        """Test trends command shows not implemented message."""
        result = runner.invoke(app, ["trends"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout.lower()

    def test_trends_valid_window(self) -> None:
        """Test trends command with valid window options."""
        for window in ["1h", "6h", "24h", "7d"]:
            result = runner.invoke(app, ["trends", "--window", window])
            assert result.exit_code == 0
            assert window in result.stdout

    def test_trends_invalid_window(self) -> None:
        """Test trends command rejects invalid window."""
        result = runner.invoke(app, ["trends", "--window", "2h"])
        assert result.exit_code == 1
        assert "Invalid window" in result.stdout
