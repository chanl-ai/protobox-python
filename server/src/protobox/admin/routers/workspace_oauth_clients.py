"""Workspace-scoped OAuth client management endpoints."""

from typing import List, Optional, Any
from datetime import datetime
import secrets
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from loguru import logger
from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..database.connection import DatabaseConnection, get_database_connection
from ..models.mcp_oauth import MCPOAuthClient
from .workspace import verify_workspace_access, get_workspace_id, get_current_user


# Create workspace-scoped router
# NOTE: OAuth clients are at /oauth-clients, NOT /integrations/oauth/clients
# The /integrations path is reserved for integration management and callbacks only
workspace_oauth_router = APIRouter(
    prefix="/workspaces/{workspace_id}/oauth-clients",
    tags=["OAuth Clients"]
)


class CreateOAuthClientRequest(BaseModel):
    """Request model for creating an OAuth client."""
    client_name: str
    redirect_uris: List[str]
    description: Optional[str] = None
    logo_uri: Optional[str] = None
    client_uri: Optional[str] = None
    scopes: Optional[List[str]] = None
    token_endpoint_auth_method: Optional[str] = "none"
    client_type: Optional[str] = "public"


class OAuthClientResponse(BaseModel):
    """Response model for OAuth client."""
    client_id: str
    client_name: str
    redirect_uris: List[str]
    allowed_scopes: List[str]
    description: Optional[str] = None
    logo_uri: Optional[str] = None
    client_uri: Optional[str] = None
    created_at: str
    last_used_at: Optional[str] = None
    status: str


class CreateOAuthClientResponse(BaseModel):
    """Response model for creating an OAuth client."""
    client_id: str
    client_secret: Optional[str] = None  # Only for confidential clients
    client_name: str
    redirect_uris: List[str]
    allowed_scopes: List[str]
    created_at: str
    message: str


@workspace_oauth_router.get("", response_model=List[OAuthClientResponse])
async def list_oauth_clients(
    request: Request,
    workspace_id: str = Depends(get_workspace_id),
    user_id: str = Depends(get_current_user),
    db = Depends(get_database_connection),
) -> List[OAuthClientResponse]:
    """List all OAuth clients for the workspace."""
    from ..services.mcp_oauth_service import MCPOAuthService
    
    oauth_service = MCPOAuthService(db.database)
    
    # Get all clients for this workspace
    clients = await oauth_service.list_workspace_clients(workspace_id)
    
    return [
        OAuthClientResponse(
            client_id=client.client_id,
            client_name=client.client_name,
            redirect_uris=client.redirect_uris,
            allowed_scopes=client.allowed_scopes,
            description=client.description,
            logo_uri=client.logo_uri,
            client_uri=client.client_uri,
            created_at=client.created_at.isoformat(),
            last_used_at=client.last_used_at.isoformat() if client.last_used_at else None,
            status=client.status,
        )
        for client in clients
    ]


@workspace_oauth_router.post("", response_model=CreateOAuthClientResponse)
async def create_oauth_client(
    req: Request,
    request: CreateOAuthClientRequest,
    workspace_id: str = Depends(get_workspace_id),
    user_id: str = Depends(get_current_user),
    db = Depends(get_database_connection),
) -> CreateOAuthClientResponse:
    """Create a new OAuth client for the workspace."""
    
    # Generate client ID
    client_id = f"mcp_{secrets.token_hex(16)}"
    
    # Determine client type
    client_type = request.client_type or ("confidential" if request.token_endpoint_auth_method != "none" else "public")
    
    # Generate client secret for confidential clients
    client_secret = None
    client_secret_hash = ""  # Empty string for public clients
    if client_type == "confidential":
        client_secret = secrets.token_urlsafe(32)
        client_secret_hash = bcrypt.hashpw(client_secret.encode(), bcrypt.gensalt()).decode()
    
    # Create the client
    client = MCPOAuthClient(
        client_id=client_id,
        client_name=request.client_name,
        client_secret_hash=client_secret_hash or "",  # Ensure it's never None
        client_type=client_type,
        redirect_uris=request.redirect_uris,
        allowed_scopes=request.scopes or ["mcp:read", "mcp:execute"],
        token_endpoint_auth_method="client_secret_post" if client_type == "confidential" else "client_secret_basic",
        workspace_id=workspace_id,
        user_id=user_id,  # MCPOAuthClient uses user_id not owner_id
        created_by=user_id,
        description=request.description,
        logo_uri=request.logo_uri,
        client_uri=request.client_uri,
        created_at=datetime.utcnow(),
        status="active",
    )
    
    # Save to database
    from ..services.mcp_oauth_service import MCPOAuthService
    oauth_service = MCPOAuthService(db.database)
    await oauth_service.create_client_from_model(client)
    
    return CreateOAuthClientResponse(
        client_id=client_id,
        client_secret=client_secret,  # Only returned once!
        client_name=client.client_name,
        redirect_uris=client.redirect_uris,
        allowed_scopes=client.allowed_scopes,
        created_at=client.created_at.isoformat(),
        message="OAuth client created successfully. Save the client_secret - it won't be shown again!",
    )


@workspace_oauth_router.delete("/{client_id}")
async def revoke_oauth_client(
    request: Request,
    client_id: str,
    workspace_id: str = Depends(get_workspace_id),
    user_id: str = Depends(get_current_user),
    db = Depends(get_database_connection),
) -> dict:
    """Revoke an OAuth client."""
    from ..services.mcp_oauth_service import MCPOAuthService
    oauth_service = MCPOAuthService(db.database)
    
    # Get the client
    client = await oauth_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth client not found")
    
    # Check if client belongs to this workspace
    if client.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this client")
    
    # Revoke the client (pass workspace_id and user_id as required)
    success = await oauth_service.revoke_client(client_id, workspace_id, user_id)
    
    if not success:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this client or client not found")
    
    return {"message": f"OAuth client {client_id} has been revoked"}


class OAuthClientStats(BaseModel):
    """OAuth clients statistics response."""
    total_clients: int = 0
    active_clients: int = 0
    inactive_clients: int = 0
    clients_by_type: dict[str, int] = {}
    recent_authorizations: int = 0  # Last 7 days


@workspace_oauth_router.get("/stats", response_model=OAuthClientStats)
async def get_oauth_clients_stats(
    request: Request,
    workspace_id: str = Depends(get_workspace_id),
    current_user: str = Depends(get_current_user),
    db: DatabaseConnection = Depends(get_database_connection)
):
    """Get OAuth clients statistics for the workspace."""
    try:
        collection = db.database.mcp_oauth_clients
        
        # Total clients count for this workspace
        total_count = await collection.count_documents({
            "workspace_id": workspace_id,
            "deleted_at": {"$exists": False}
        })
        
        # Active clients count (not revoked) for this workspace
        active_count = await collection.count_documents({
            "workspace_id": workspace_id,
            "deleted_at": {"$exists": False},
            "revoked": False
        })
        
        # Inactive clients count
        inactive_count = total_count - active_count
        
        # Count by client type (public vs confidential) for this workspace
        pipeline = [
            {"$match": {
                "workspace_id": workspace_id,
                "deleted_at": {"$exists": False}
            }},
            {"$group": {"_id": "$client_type", "count": {"$sum": 1}}}
        ]
        by_type_results = await collection.aggregate(pipeline).to_list(None)
        clients_by_type = {result["_id"] or "unknown": result["count"] for result in by_type_results}
        
        # Recent authorizations (last 7 days) - placeholder for now
        recent_authorizations = 0
        
        return OAuthClientStats(
            total_clients=total_count,
            active_clients=active_count,
            inactive_clients=inactive_count,
            clients_by_type=clients_by_type,
            recent_authorizations=recent_authorizations
        )
        
    except Exception as e:
        logger.error(f"Failed to get OAuth clients stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get OAuth clients statistics"
        )

