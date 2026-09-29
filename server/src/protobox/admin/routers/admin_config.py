"""Admin configuration endpoints for runtime config changes."""


from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from ..auth.auth_config import (
    AuthConfig,
    get_auth_config,
    reset_auth_config,
    set_auth_config,
)
from ..config import settings

router = APIRouter(prefix="/admin/config", tags=["Admin Config"])


class AuthConfigUpdate(BaseModel):
    """Request to update auth configuration."""

    test_mode: bool | None = None
    allow_test_tokens: bool | None = None


class ConfigResponse(BaseModel):
    """Configuration response."""

    auth: AuthConfig
    environment: str


async def verify_admin_secret(x_admin_secret: str | None = Header(None)) -> bool:
    """Verify admin secret for config changes."""
    admin_secret = settings.admin_config_secret

    # If no secret is configured, allow in development only
    if not admin_secret:
        if not settings.is_development():
            raise HTTPException(
                status_code=403,
                detail="Admin config endpoints are disabled in production without ADMIN_CONFIG_SECRET",
            )
        return True

    # Verify the provided secret
    if x_admin_secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    return True


@router.get("/", response_model=ConfigResponse)
async def get_config(_: bool = Depends(verify_admin_secret)):
    """Get current configuration."""
    return ConfigResponse(auth=get_auth_config(), environment=settings.environment)


@router.post("/auth", response_model=AuthConfig)
async def update_auth_config(update: AuthConfigUpdate, _: bool = Depends(verify_admin_secret)):
    """Update authentication configuration at runtime."""
    config = get_auth_config()

    # Build update dict (removed deprecated mode field)
    updates = {}
    if update.test_mode is not None:
        updates["test_mode"] = update.test_mode
    if update.allow_test_tokens is not None:
        updates["allow_test_tokens"] = update.allow_test_tokens

    # Apply updates
    new_config = config.override(**updates)
    set_auth_config(new_config)

    return new_config


@router.post("/auth/reset", response_model=AuthConfig)
async def reset_auth_config_endpoint(_: bool = Depends(verify_admin_secret)):
    """Reset auth configuration to environment defaults."""
    reset_auth_config()
    return get_auth_config()


# Removed deprecated quick_switch_auth_mode endpoint - now always uses Firebase authentication
