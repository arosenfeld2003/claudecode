"""Health check module for OpenClaw Moltbook Monitor.

Provides health checking functionality for:
- Database connectivity (DuckDB)
- Proxy connectivity (Nginx reverse proxy)
- Overall system health

Used by both CLI commands and the HTTP health endpoint.
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


class HealthChecker:
    """Health checker for monitoring system components.

    Checks:
    - Database: DuckDB file exists and is accessible
    - Proxy: Can reach the reverse proxy health endpoint
    - System: Overall system health summary
    """

    def __init__(
        self,
        db_path: str | None = None,
        proxy_url: str | None = None,
    ) -> None:
        """Initialize health checker.

        Args:
            db_path: Path to DuckDB database file. Defaults to /app/data/monitor.duckdb
            proxy_url: URL of the reverse proxy health endpoint.
                      Defaults to http://proxy:8080/health
        """
        db_path_str = db_path or os.getenv("MONITOR_DB_PATH") or "/app/data/monitor.duckdb"
        self.db_path = Path(db_path_str)
        self.proxy_url: str = proxy_url or os.getenv("PROXY_HEALTH_URL") or "http://proxy:8080/health"

    def check_database(self) -> dict[str, Any]:
        """Check database connectivity.

        Returns:
            Dict with 'healthy' bool and status details.
        """
        try:
            import duckdb

            # Check if database file exists or can be created
            db_dir = self.db_path.parent
            if not db_dir.exists():
                return {
                    "healthy": False,
                    "message": f"Database directory does not exist: {db_dir}",
                }

            # Try to connect to the database
            conn = duckdb.connect(str(self.db_path), read_only=False)

            # Simple query to verify connection
            result = conn.execute("SELECT 1 AS health_check").fetchone()
            conn.close()

            if result and result[0] == 1:
                return {
                    "healthy": True,
                    "message": f"Connected to {self.db_path}",
                    "path": str(self.db_path),
                }
            else:
                return {
                    "healthy": False,
                    "message": "Database query returned unexpected result",
                }

        except ImportError:
            return {
                "healthy": False,
                "message": "DuckDB module not installed",
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Database error: {e!s}",
            }

    def check_proxy(self) -> dict[str, Any]:
        """Check reverse proxy connectivity.

        Returns:
            Dict with 'healthy' bool and status details.
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(self.proxy_url)

                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "message": "Proxy is reachable",
                        "url": self.proxy_url,
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                    }
                else:
                    return {
                        "healthy": False,
                        "message": f"Proxy returned status {response.status_code}",
                        "url": self.proxy_url,
                    }

        except httpx.ConnectError:
            return {
                "healthy": False,
                "message": "Cannot connect to proxy (connection refused)",
                "url": self.proxy_url,
            }
        except httpx.TimeoutException:
            return {
                "healthy": False,
                "message": "Proxy connection timed out",
                "url": self.proxy_url,
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Proxy error: {e!s}",
                "url": self.proxy_url,
            }

    def check_all(self) -> dict[str, Any]:
        """Run all health checks.

        Returns:
            Dict with status of all components and overall health.
        """
        db_status = self.check_database()
        proxy_status = self.check_proxy()

        # Overall health is true only if all components are healthy
        # Note: For development, we may relax proxy requirement
        overall_healthy = db_status["healthy"]

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "healthy": overall_healthy,
            "database": db_status,
            "proxy": proxy_status,
        }

    def to_json_response(self) -> dict[str, Any]:
        """Get health status as JSON-serializable response.

        Suitable for HTTP health endpoint responses.
        """
        status = self.check_all()
        return {
            "status": "healthy" if status["healthy"] else "unhealthy",
            "timestamp": status["timestamp"],
            "components": {
                "database": status["database"],
                "proxy": status["proxy"],
            },
        }
