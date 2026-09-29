"""
CORS configuration.

Allowed origins come from CORS_ALLOWED_ORIGINS (comma-separated). In development the
local dashboard, docs and MCP Inspector ports are added so a fresh checkout works
without configuration. No hosted origin is ever added implicitly: an origin that is
allowed with credentials can act as any signed-in user of this deployment.
"""

import os

DEVELOPMENT_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3010",
    "http://localhost:6274",  # MCP Inspector
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3010",
    "http://127.0.0.1:6274",
]


def get_cors_origins() -> list[str]:
    cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
    origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]

    env = os.getenv("ENV", os.getenv("ENVIRONMENT", "development"))
    if env in ["development", "dev_test"]:
        origins.extend(DEVELOPMENT_ORIGINS)

    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        origins.append(frontend_url.rstrip("/"))

    return list(dict.fromkeys(origins))
