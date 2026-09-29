"""
Authentication router for sessionless JWT-based auth.

Provides endpoints for:
- Firebase token exchange
- Token refresh
- Token validation
- API key management
"""

from bson import ObjectId
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import HTTPBearer
from loguru import logger
from pydantic import BaseModel

from ..auth.dependencies import get_current_user, require_authentication
from ..auth.firebase_auth import (
    FirebaseAuth,
    FirebaseTokenExchangeRequest,
    TokenExchangeResponse,
    get_firebase_auth,
)
from ..auth.jwt_auth import JWTAuth, get_jwt_auth
from ..auth.models import User
from ..database.connection import get_database_connection


def get_db():
    """Get database connection."""
    db_conn = get_database_connection()
    return db_conn.database


router = APIRouter(tags=["Authentication"])
security = HTTPBearer(auto_error=False)


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str


class ValidateTokenResponse(BaseModel):
    """Response model for token validation."""

    valid: bool
    uid: str | None = None
    email: str | None = None
    workspace_id: str | None = None
    token_type: str | None = None
    expires_at: int | None = None


@router.post("/exchange", response_model=TokenExchangeResponse)
async def exchange_firebase_token(
    request: FirebaseTokenExchangeRequest,
    response: Response,
    firebase_auth: FirebaseAuth = Depends(get_firebase_auth),
    jwt_auth: JWTAuth = Depends(get_jwt_auth),
    db=Depends(get_db),
):
    """
    Exchange a Firebase ID token for custom JWT tokens.

    This is the primary authentication endpoint. After initial Firebase
    authentication, clients exchange the Firebase token for our custom
    JWT tokens which are used for all subsequent API calls.

    Returns:
        - access_token: Short-lived token (1 hour) for API access
        - refresh_token: Long-lived token (30 days) for refreshing access
        - user: Basic user information
    """
    # Exchange Firebase token for custom JWTs
    token_response = await firebase_auth.exchange_token(request.firebase_token, jwt_auth, db)

    if not token_response:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

    # Set refresh token as HTTP-only cookie for security
    response.set_cookie(
        key="refresh_token",
        value=token_response.refresh_token,
        httponly=True,  # Note: lowercase
        secure=True,  # Always use secure in production
        samesite="lax",
        max_age=30 * 24 * 60 * 60,  # 30 days
        path="/api/v1/auth",  # Only send to auth endpoints
    )

    return token_response


@router.post("/refresh", response_model=TokenExchangeResponse)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    request_body: RefreshTokenRequest | None = None,
    jwt_auth: JWTAuth = Depends(get_jwt_auth),
):
    """
    Refresh an access token using a refresh token.

    The refresh token can be provided either:
    1. As an HTTP-only cookie (preferred for web clients)
    2. In the request body (for mobile/CLI clients)

    Returns:
        - access_token: New short-lived token
        - refresh_token: Same refresh token (rotated in future)
        - user: Basic user information
    """
    # Get refresh token from cookie or body
    token = refresh_token or (request_body.refresh_token if request_body else None)

    if not token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    # Validate refresh token
    payload = jwt_auth.validate_refresh_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Create new access token
    new_access_token = jwt_auth.create_access_token(
        uid=payload["uid"], email=payload.get("email"), workspace_id=payload.get("workspace_id")
    )

    # TODO: Implement refresh token rotation for enhanced security
    # new_refresh_token = jwt_auth.create_refresh_token(...)

    return TokenExchangeResponse(
        access_token=new_access_token,
        refresh_token=token,  # Return same token for now
        expires_in=3600,
        user={"id": payload["uid"], "email": payload.get("email")},
    )


@router.get("/validate", response_model=ValidateTokenResponse)
async def validate_token(current_user: User | None = Depends(get_current_user)):
    """
    Validate the current access token.

    This endpoint can be used to check if a token is still valid
    and get basic information about the authenticated user.
    """
    if not current_user:
        return ValidateTokenResponse(valid=False)

    return ValidateTokenResponse(
        valid=True,
        uid=current_user.id,
        email=current_user.email,
        workspace_id=current_user.metadata.get("workspace_id") if current_user.metadata else None,
        token_type="access",
    )


@router.post("/switch-workspace", response_model=TokenExchangeResponse)
async def switch_workspace(
    request: dict,
    current_user: User = Depends(require_authentication),
    jwt_auth: JWTAuth = Depends(get_jwt_auth),
    db=Depends(get_db),
):
    """
    Switch to a different workspace by generating new tokens with the updated workspace_id.
    
    This is necessary because the workspace_id is embedded in the JWT token claims.
    When switching workspaces, we need new tokens with the correct workspace_id.
    """
    workspace_id = request.get("workspace_id")
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    
    # Verify user has access to this workspace
    workspaces_collection = db.workspaces
    workspace = await workspaces_collection.find_one({
        "_id": ObjectId(workspace_id) if ObjectId.is_valid(workspace_id) else workspace_id,
        "$or": [
            {"owner_id": current_user.id},
            {"members.user_id": current_user.id}
        ]
    })
    
    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied to workspace")
    
    # Update user's last workspace preference
    users_collection = db.users
    await users_collection.update_one(
        {"firebase_uid": current_user.id},
        {"$set": {"preferences.last_workspace_id": workspace["_id"]}}
    )
    
    # Create new tokens with the updated workspace_id
    new_access_token = jwt_auth.create_access_token(
        uid=current_user.id,
        email=current_user.email,
        workspace_id=str(workspace["_id"]),
        additional_claims=current_user.metadata or {}
    )
    
    new_refresh_token = jwt_auth.create_refresh_token(
        uid=current_user.id,
        email=current_user.email,
        workspace_id=str(workspace["_id"])
    )
    
    return TokenExchangeResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=3600,
        user={
            "id": current_user.id,
            "email": current_user.email,
            "workspace_id": str(workspace["_id"])
        }
    )


@router.post("/revoke")
async def revoke_token(
    response: Response,
    refresh_token: str | None = Cookie(None),
    current_user: User = Depends(require_authentication),
):
    """
    Revoke tokens (logout).

    For sessionless auth, this primarily:
    1. Clears the refresh token cookie
    2. Optionally adds token to blacklist (not implemented yet)

    The client should also delete their access token.
    """
    # Clear refresh token cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")

    # TODO: Implement token blacklist for critical security events
    # await redis.setex(f"blacklist:{token}", ttl, "revoked")

    logger.info(f"User {current_user.email} logged out")

    return {"message": "Successfully logged out"}


# API Key Management Endpoints (TODO: Implement)


@router.get("/keys")
async def list_api_keys(current_user: User = Depends(require_authentication)):
    """
    List API keys for the current user's workspace.

    TODO: Implement API key storage and retrieval
    """
    return {"keys": [], "message": "API key management coming soon"}


@router.post("/keys")
async def create_api_key(current_user: User = Depends(require_authentication)):
    """
    Create a new API key for programmatic access.

    TODO: Implement API key generation and storage
    """
    return {"message": "API key creation coming soon"}


@router.delete("/keys/{key_id}")
async def revoke_api_key(key_id: str, current_user: User = Depends(require_authentication)):
    """
    Revoke an API key.

    TODO: Implement API key revocation
    """
    return {"message": f"API key {key_id} revocation coming soon"}
