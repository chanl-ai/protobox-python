"""MCP Token management endpoints."""

from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth.dependencies import require_authentication
from ..auth.mcp_auth import MCPAuthService
from ..database.connection import get_database_connection
from ..middleware.team_auth import require_workspace_access
from ..models.team_member import WorkspaceMember

router = APIRouter(prefix="/workspaces/{workspace_id}/mcp-tokens", tags=["MCP Tokens"], redirect_slashes=False)


class CreateMCPTokenRequest(BaseModel):
    """Request model for creating an MCP token."""

    name: str
    description: str | None = None
    expires_in_days: int | None = None  # None means never expires (long-term default)
    scopes: list[str] | None = None


class MCPTokenResponse(BaseModel):
    """Response model for MCP token (without sensitive data)."""

    token_id: str
    name: str
    description: str | None
    workspace_id: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None
    usage_count: int
    status: str


class CreateMCPTokenResponse(BaseModel):
    """Response when creating a new MCP token."""

    token: str  # Plain token - only shown once!
    token_id: str
    name: str
    workspace_id: str
    mcp_url: str  # Full URL to use with MCP clients
    expires_at: datetime | None
    message: str = "Save this token securely. It won't be shown again."


@router.post("", response_model=CreateMCPTokenResponse)
@router.post("/", response_model=CreateMCPTokenResponse)
async def create_mcp_token(
    workspace_id: str,
    request: CreateMCPTokenRequest,
    member: WorkspaceMember = Depends(require_workspace_access),
):
    """
    Create a new MCP token for the workspace.

    The returned token is only shown once and should be saved securely.
    Use the `mcp_url` field to connect AI assistants to your workspace.
    """
    # Validate workspace_id is a valid MongoDB ObjectId
    try:
        ObjectId(workspace_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace ID format: {workspace_id}. Must be a valid MongoDB ObjectId.",
        )

    # TODO: Verify user has permission to create tokens for this workspace

    db = get_database_connection()

    # Create the token
    result = await MCPAuthService.create_mcp_token(
        db=db.database,
        workspace_id=workspace_id,
        user_id=member.user_id,
        name=request.name,
        description=request.description,
        expires_in_days=request.expires_in_days,
        scopes=request.scopes,
    )

    # Audit log the token creation
    await db.database["audit_logs"].insert_one(
        {
            "event": "mcp_token.created",
            "workspace_id": workspace_id,
            "user_id": member.user_id,
            "token_id": result["token_id"],
            "token_name": request.name,
            "timestamp": datetime.now(UTC),
        }
    )

    return CreateMCPTokenResponse(
        token=result["token"],
        token_id=result["token_id"],
        name=result["name"],
        workspace_id=result["workspace_id"],
        mcp_url=result["mcp_url"],
        expires_at=result["expires_at"],
    )


@router.get("", response_model=list[MCPTokenResponse])
@router.get("/", response_model=list[MCPTokenResponse])
async def list_mcp_tokens(
    workspace_id: str,
    member: WorkspaceMember = Depends(require_workspace_access),
    include_revoked: bool = Query(False, description="Include revoked tokens"),
):
    """
    List all MCP tokens for the workspace.

    Note: The actual token values are never exposed after creation.
    """
    # Validate workspace_id is a valid MongoDB ObjectId
    try:
        ObjectId(workspace_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace ID format: {workspace_id}. Must be a valid MongoDB ObjectId.",
        )

    # TODO: Verify user has permission to view tokens for this workspace

    db = get_database_connection()

    # Get tokens
    query = {"workspace_id": workspace_id}
    if not include_revoked:
        query["status"] = {"$ne": "revoked"}

    tokens = await db.database["mcp_tokens"].find(query).to_list(length=100)

    # Convert to response models (excluding sensitive data)
    return [
        MCPTokenResponse(
            token_id=token["token_id"],
            name=token["name"],
            description=token.get("description"),
            workspace_id=token["workspace_id"],
            scopes=token["scopes"],
            expires_at=token.get("expires_at"),
            created_at=token["created_at"],
            last_used_at=token.get("last_used_at"),
            usage_count=token.get("usage_count", 0),
            status=token["status"],
        )
        for token in tokens
    ]


@router.delete("/{token_id}")
async def revoke_mcp_token(
    workspace_id: str, token_id: str, member: WorkspaceMember = Depends(require_workspace_access)
):
    """
    Revoke an MCP token.

    Revoked tokens cannot be used for authentication.
    """
    # Validate workspace_id is a valid MongoDB ObjectId
    try:
        ObjectId(workspace_id)
    except InvalidId:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid workspace ID format: {workspace_id}. Must be a valid MongoDB ObjectId.",
        )

    # TODO: Verify user has permission to revoke tokens for this workspace

    db = get_database_connection()

    # Check token exists and belongs to workspace
    token = await db.database["mcp_tokens"].find_one(
        {"token_id": token_id, "workspace_id": workspace_id}
    )

    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    if token["status"] == "revoked":
        raise HTTPException(status_code=400, detail="Token is already revoked")

    # Revoke the token
    success = await MCPAuthService.revoke_token(db.database, token_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to revoke token")

    # Audit log the revocation
    await db.database["audit_logs"].insert_one(
        {
            "event": "mcp_token.revoked",
            "workspace_id": workspace_id,
            "user_id": member.user_id,
            "token_id": token_id,
            "timestamp": datetime.now(UTC),
        }
    )

    return {"message": f"Token {token_id} has been revoked"}


# ==================== MCP Tokens Stats Endpoints ====================

class MCPTokenStats(BaseModel):
    """MCP tokens statistics model."""
    total_tokens: int = 0
    active_tokens: int = 0
    expired_tokens: int = 0
    tokens_by_status: dict[str, int] = {}
    recent_usage: int = 0  # Last 7 days


@router.get("/stats", response_model=MCPTokenStats)
async def get_mcp_tokens_stats(
    workspace_id: str,
    member: WorkspaceMember = Depends(require_workspace_access),
    db=Depends(get_database_connection)
):
    """Get MCP tokens statistics for the workspace."""
    try:
        collection = db.database.mcp_tokens
        
        # Total tokens count
        total_count = await collection.count_documents({
            "workspace_id": workspace_id,
            "status": {"$ne": "deleted"}
        })
        
        # Active tokens count
        active_count = await collection.count_documents({
            "workspace_id": workspace_id,
            "status": "active"
        })
        
        # Expired tokens count
        expired_count = await collection.count_documents({
            "workspace_id": workspace_id,
            "status": "expired"
        })
        
        # Usage stats by time periods (last 7 days, 30 days)
        from datetime import datetime, timedelta
        now = datetime.now(UTC)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        # Count tokens used in different periods
        usage_last_7_days = await collection.count_documents({
            "workspace_id": workspace_id,
            "last_used_at": {"$gte": seven_days_ago},
            "status": {"$ne": "deleted"}
        })
        
        usage_last_30_days = await collection.count_documents({
            "workspace_id": workspace_id, 
            "last_used_at": {"$gte": thirty_days_ago},
            "status": {"$ne": "deleted"}
        })
        
        usage_stats = {
            "last_7_days": usage_last_7_days,
            "last_30_days": usage_last_30_days,
            "never_used": total_count - usage_last_30_days
        }
        
        # Create tokens by status dict
        tokens_by_status = {
            "active": active_count,
            "expired": expired_count
        }
        
        return MCPTokenStats(
            total_tokens=total_count,
            active_tokens=active_count,
            expired_tokens=expired_count,
            tokens_by_status=tokens_by_status,
            recent_usage=usage_last_7_days
        )
        
    except Exception as e:
        logger.error(f"Failed to get MCP tokens stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get MCP tokens statistics"
        )
