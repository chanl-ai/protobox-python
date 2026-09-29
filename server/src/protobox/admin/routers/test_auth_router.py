"""
Test authentication router for development and testing purposes.

IMPORTANT: This router should only be enabled in development/test environments.
DO NOT USE IN PRODUCTION.
"""

import os

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from ..auth.jwt_auth import get_jwt_auth

# Only enable this router in development/test environments
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
AUTH_TEST_MODE = os.getenv("AUTH_TEST_MODE", "false").lower() == "true"

if ENVIRONMENT not in ["development", "dev", "test", "local", "staging"] or not AUTH_TEST_MODE:
    router = None
    logger.warning("Test auth router is disabled in production environments")
else:
    router = APIRouter(prefix="/test-auth", tags=["Test Auth"])
    logger.warning("⚠️  TEST AUTH ROUTER ENABLED - DO NOT USE IN PRODUCTION")


class TestTokenRequest(BaseModel):
    """Request model for creating test tokens."""

    uid: str = "test-user-123"
    email: str = "test@example.com"
    workspace_id: str | None = "test-workspace-123"
    role: str = "admin"
    permissions: list[str] = ["read", "write", "admin"]


class TestTokenResponse(BaseModel):
    """Response model for test tokens."""

    access_token: str
    token_type: str = "bearer"
    test_mode: bool = True
    warning: str = "This is a test token. Do not use in production."


if router:

    @router.post("/create-token", response_model=TestTokenResponse)
    async def create_test_token(request: TestTokenRequest = TestTokenRequest()):
        """
        Create a test JWT token for development/testing.

        WARNING: This endpoint should only be used in development environments.
        """
        jwt_auth = get_jwt_auth()

        if not jwt_auth.test_mode:
            raise HTTPException(
                status_code=403, detail="Test tokens can only be created in test mode"
            )

        try:
            token = jwt_auth.create_test_token(
                uid=request.uid,
                email=request.email,
                workspace_id=request.workspace_id,
                role=request.role,
                permissions=request.permissions,
            )

            logger.warning(f"Test token created for user: {request.email}")

            return TestTokenResponse(
                access_token=token,
                token_type="bearer",
                test_mode=True,
                warning="This is a test token. Do not use in production.",
            )

        except Exception as e:
            logger.error(f"Error creating test token: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create test token: {str(e)}")

    @router.get("/info")
    async def get_test_auth_info():
        """Get information about the test auth configuration."""
        jwt_auth = get_jwt_auth()

        return {
            "test_mode": jwt_auth.test_mode,
            "environment": jwt_auth.environment,
            "warning": "Test auth is enabled. Do not use in production.",
            "simple_test_token": "Use 'Bearer test-token' for a simple test user",
            "custom_test_token_endpoint": "/test-auth/create-token",
        }
