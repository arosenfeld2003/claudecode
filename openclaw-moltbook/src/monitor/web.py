"""FastAPI web application for health checks and future dashboard.

Provides:
- /health endpoint for container health checks
- /api/health for detailed health status
- /admin/* endpoints for admin credential management (HTTP Basic auth)
"""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from monitor.admin_auth import authenticate, hash_password, is_password_set, save_password_hash
from monitor.health import HealthChecker

app = FastAPI(
    title="OpenClaw Moltbook Monitor",
    description="Monitor and analyze the Moltbook platform",
    version="0.1.0",
)

_security = HTTPBasic()


def _require_admin(credentials: Annotated[HTTPBasicCredentials, Depends(_security)]) -> str:
    """FastAPI dependency that enforces HTTP Basic admin authentication."""
    valid = authenticate(credentials.username, credentials.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class ChangePasswordRequest(BaseModel):
    new_password: str


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check() -> JSONResponse:
    """Simple health check for container orchestration (200 healthy, 503 unhealthy)."""
    checker = HealthChecker()
    result = checker.check_all()

    if result["healthy"]:
        return JSONResponse(
            content={"status": "healthy", "timestamp": result["timestamp"]},
            status_code=200,
        )
    return JSONResponse(
        content={"status": "unhealthy", "timestamp": result["timestamp"]},
        status_code=503,
    )


@app.get("/api/health")
async def detailed_health() -> JSONResponse:
    """Detailed health check with per-component status."""
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


# ---------------------------------------------------------------------------
# Admin endpoints (require HTTP Basic auth)
# ---------------------------------------------------------------------------


@app.get("/admin/status")
async def admin_status(
    _username: Annotated[str, Depends(_require_admin)],
) -> dict[str, object]:
    """Show admin authentication status (requires valid credentials)."""
    return {
        "authenticated": True,
        "password_set": is_password_set(),
    }


@app.post("/admin/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    _username: Annotated[str, Depends(_require_admin)],
) -> None:
    """Change the admin password (requires current valid credentials).

    To reset without the current password, use: monitor admin reset-password
    """
    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_password must be at least 8 characters",
        )
    save_password_hash(hash_password(body.new_password))
