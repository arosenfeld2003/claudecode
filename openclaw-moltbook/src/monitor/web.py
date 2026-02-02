"""FastAPI web application for health checks and future dashboard.

Provides:
- /health endpoint for container health checks
- /api/health for detailed health status
- Future: Web dashboard for non-technical users
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from monitor.health import HealthChecker

app = FastAPI(
    title="OpenClaw Moltbook Monitor",
    description="Monitor and analyze the Moltbook platform",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> JSONResponse:
    """Simple health check endpoint for container orchestration.

    Returns 200 if healthy, 503 if unhealthy.
    """
    checker = HealthChecker()
    status = checker.check_all()

    if status["healthy"]:
        return JSONResponse(
            content={"status": "healthy", "timestamp": status["timestamp"]},
            status_code=200,
        )
    else:
        return JSONResponse(
            content={"status": "unhealthy", "timestamp": status["timestamp"]},
            status_code=503,
        )


@app.get("/api/health")
async def detailed_health() -> JSONResponse:
    """Detailed health check with component status.

    Returns full health information for debugging.
    """
    checker = HealthChecker()
    return JSONResponse(content=checker.to_json_response())


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "OpenClaw Moltbook Monitor",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
