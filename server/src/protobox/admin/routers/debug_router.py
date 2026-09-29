"""Debug router for development - prints configuration (with redacted secrets)."""

import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from ...config.settings import Config

router = APIRouter(
    prefix="/debug",
    tags=["debug"],
)


def redact_sensitive(value: Any, key: str = "") -> Any:
    """Redact sensitive values while keeping structure."""
    sensitive_keys = [
        "secret",
        "key",
        "password",
        "token",
        "credential",
        "private",
        "service_account",
    ]

    if isinstance(value, dict):
        return {k: redact_sensitive(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        # Check if key contains sensitive words
        for sensitive in sensitive_keys:
            if sensitive in key.lower():
                if value:
                    # Show first 4 chars and length
                    return f"{value[:4]}...({len(value)} chars)" if len(value) > 4 else "***"
                return None
        return value
    return value


@router.get("/config")
async def get_config():
    """Get current configuration (with redacted secrets)."""
    if os.getenv("ENVIRONMENT") not in ["development", "dev_test"]:
        raise HTTPException(status_code=403, detail="Debug endpoints only available in development")

    config = Config.from_env()
    config_dict = config.dict()

    # Log the config to server logs
    logger.info("=== Current Configuration ===")
    logger.info(json.dumps(redact_sensitive(config_dict), indent=2))

    return {
        "environment": os.getenv("ENVIRONMENT"),
        "config": redact_sensitive(config_dict),
        "available_env_vars": sorted(
            [
                k
                for k in os.environ
                if k.startswith(("MCP_", "AUTH_", "FIREBASE_", "JWT_", "ENVIRONMENT"))
            ]
        ),
    }


@router.get("/env")
async def get_environment():
    """Get environment variables (redacted)."""
    if os.getenv("ENVIRONMENT") not in ["development", "dev_test"]:
        raise HTTPException(status_code=403, detail="Debug endpoints only available in development")

    env_vars = {}
    for key in sorted(os.environ.keys()):
        if key.startswith(("MCP_", "AUTH_", "FIREBASE_", "JWT_", "ENVIRONMENT", "TEST")):
            env_vars[key] = redact_sensitive(os.environ[key], key)

    # Log to server logs
    logger.info("=== Environment Variables ===")
    for key, value in env_vars.items():
        logger.info(f"{key}={value}")

    return env_vars
