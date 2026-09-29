"""Monitoring and health check endpoints."""

import os
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException

from ...monitoring import capture_exception
from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..config import settings

router = APIRouter(tags=["monitoring"])


# Monitoring API Key Authentication
async def verify_monitoring_key(x_monitoring_key: str | None = Header(None)):
    """Verify monitoring API key."""
    if not x_monitoring_key:
        raise HTTPException(401, "Missing X-Monitoring-Key header")

    if not settings.has_monitoring_key:
        raise HTTPException(503, "Monitoring not configured")

    if x_monitoring_key != settings.monitoring_api_key:
        raise HTTPException(401, "Invalid monitoring key")

    return True


# Track server start time
SERVER_START_TIME = time.time()


@router.post("/test-error")
async def test_error(current_user: User = Depends(require_authentication)):
    """Test endpoint to trigger an error for monitoring verification."""
    env = os.getenv("ENV", "development")
    if env not in ["dev", "dev_test", "staging"]:
        raise HTTPException(
            status_code=403, detail="Test errors only allowed in non-production environments"
        )

    # This will be captured by Sentry
    try:
        raise Exception(
            f"Test error triggered by user {current_user.id} for monitoring verification"
        )
    except Exception as e:
        capture_exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(_: bool = Depends(verify_monitoring_key)):
    """Get basic application metrics - requires monitoring API key."""
    current_time = time.time()
    uptime_seconds = current_time - SERVER_START_TIME

    # Only expose safe, non-sensitive metrics
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": os.getenv("ENV", "unknown"),
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "uptime": {
            "seconds": int(uptime_seconds),
            "human_readable": str(timedelta(seconds=int(uptime_seconds))),
        },
        # Don't expose full Python version (security risk)
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        # Only show deployment info in non-production
        "deployment": {
            "commit_sha": (
                os.getenv("COMMIT_SHA", "unknown") if os.getenv("ENV") != "production" else "hidden"
            ),
            "deployed_at": (
                os.getenv("DEPLOYED_AT", "unknown")
                if os.getenv("ENV") != "production"
                else "hidden"
            ),
        },
    }


@router.get("/ready")
async def readiness_check():
    """Kubernetes-style readiness probe."""
    # TODO: Add checks for database connectivity, cache, etc.
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Kubernetes-style liveness probe."""
    return {"status": "alive"}


@router.get("/environment")
async def environment_check(_: bool = Depends(verify_monitoring_key)):
    """Check environment configuration and CORS settings - requires monitoring API key."""
    from ..cors_config import get_cors_origins

    # Get relevant environment variables (safe to expose for debugging)
    env_vars = {
        "ENV": os.getenv("ENV", "not_set"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "not_set"),
        "CORS_ALLOWED_ORIGINS": os.getenv("CORS_ALLOWED_ORIGINS", "not_set"),
        "VERCEL_URL": os.getenv("VERCEL_URL", "not_set"),
        "VERCEL_PREVIEW_DOMAIN": os.getenv("VERCEL_PREVIEW_DOMAIN", "not_set"),
    }

    # Get computed CORS origins
    cors_origins = get_cors_origins()

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "environment_variables": env_vars,
        "computed_cors_origins": cors_origins,
        "cors_count": len(cors_origins),
        "configuration_status": "configured" if cors_origins else "not_configured",
    }
