"""Public health check endpoints - no authentication required but rate limited."""

import hashlib
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from ..health import HealthChecker
from ..startup_checks import get_startup_status

router = APIRouter(tags=["health"])

# Simple in-memory rate limiter
rate_limit_store: dict[str, list] = {}
RATE_LIMIT_REQUESTS = 10  # Max requests
RATE_LIMIT_WINDOW = 60  # Per 60 seconds


def get_client_id(request: Request) -> str:
    """Get a unique client identifier for rate limiting."""
    # Use a combination of IP and user agent
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0] if forwarded_for else request.client.host
    user_agent = request.headers.get("User-Agent", "")

    # Hash the combination for privacy
    client_string = f"{ip}:{user_agent}"
    return hashlib.sha256(client_string.encode()).hexdigest()[:16]


def check_rate_limit(client_id: str) -> bool:
    """Check if client has exceeded rate limit."""
    current_time = time.time()

    # Clean up old entries
    if client_id in rate_limit_store:
        rate_limit_store[client_id] = [
            timestamp
            for timestamp in rate_limit_store[client_id]
            if current_time - timestamp < RATE_LIMIT_WINDOW
        ]

    # Check rate limit
    if client_id not in rate_limit_store:
        rate_limit_store[client_id] = []

    if len(rate_limit_store[client_id]) >= RATE_LIMIT_REQUESTS:
        return False

    rate_limit_store[client_id].append(current_time)
    return True


@router.get("/health")
async def health_check(request: Request):
    """
    Public health check endpoint.

    Returns minimal information about service health.
    Rate limited to prevent abuse.
    """
    # Check rate limit
    client_id = get_client_id(request)
    if not check_rate_limit(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

    # Return minimal health information
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "protobox-api",
    }


@router.get("/ping")
async def ping(request: Request):
    """
    Simple ping endpoint for uptime monitoring.

    Rate limited to prevent abuse.
    """
    # Check rate limit
    client_id = get_client_id(request)
    if not check_rate_limit(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return {"pong": True}


@router.get("/startup-status")
async def startup_status_endpoint(request: Request):
    """Get startup integration check status."""
    # Check rate limit
    client_id = get_client_id(request)
    if not check_rate_limit(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return get_startup_status()


@router.get("/health-detailed")
async def detailed_health_endpoint(request: Request):
    """Get detailed health status including startup checks."""
    # Check rate limit
    client_id = get_client_id(request)
    if not check_rate_limit(client_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    health_checker = HealthChecker()
    health_status = await health_checker.get_health_status()
    
    # Add startup check results
    startup_status = get_startup_status()
    health_status["startup_checks"] = startup_status
    
    # Override overall status if startup checks failed
    if startup_status.get("status") == "failed":
        health_status["status"] = "degraded"
        health_status["startup_failure"] = True
    elif startup_status.get("status") == "degraded" and health_status.get("status") == "healthy":
        health_status["status"] = "degraded"
    
    return health_status
