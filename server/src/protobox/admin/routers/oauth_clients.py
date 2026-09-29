"""Admin API endpoints for managing MCP OAuth clients."""

from typing import List, Optional, Any
from datetime import datetime, timedelta
import secrets
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..database.connection import get_database_connection
from ..models.mcp_oauth import MCPOAuthClient


router = APIRouter(tags=["OAuth Clients"])


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


@router.get("/integrations/oauth/clients", response_model=List[OAuthClientResponse])
async def list_oauth_clients(
    current_user: User = Depends(require_authentication),
    db = Depends(get_database_connection),
) -> List[OAuthClientResponse]:
    """List all OAuth clients for the user's workspace."""
    from ..services.mcp_oauth_service import MCPOAuthService
    
    oauth_service = MCPOAuthService(db.database)
    
    # Get workspace_id from authenticated user
    workspace_id = current_user.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="User has no workspace")
    
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


@router.post("/integrations/oauth/clients", response_model=CreateOAuthClientResponse)
async def create_oauth_client(
    request: CreateOAuthClientRequest,
    current_user: User = Depends(require_authentication),
    db = Depends(get_database_connection),
) -> CreateOAuthClientResponse:
    """Create a new OAuth client for the user's workspace."""
    
    # Get workspace_id from authenticated user
    workspace_id = current_user.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="User has no workspace")
    
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
        user_id=current_user.id,  # MCPOAuthClient uses user_id not owner_id
        created_by=current_user.id,
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


@router.delete("/integrations/oauth/clients/{client_id}")
async def revoke_oauth_client(
    client_id: str,
    current_user: User = Depends(require_authentication),
    db = Depends(get_database_connection),
) -> dict:
    """Revoke an OAuth client."""
    from ..services.mcp_oauth_service import MCPOAuthService
    oauth_service = MCPOAuthService(db.database)
    
    # Get workspace_id from authenticated user
    workspace_id = current_user.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="User has no workspace")
    
    # Get the client
    client = await oauth_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth client not found")
    
    # Check if client belongs to user's workspace
    if client.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this client")
    
    # Revoke the client (pass workspace_id and user_id as required)
    success = await oauth_service.revoke_client(client_id, workspace_id, current_user.id)
    
    if not success:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this client or client not found")
    
    return {"message": f"OAuth client {client_id} has been revoked"}


@router.get("/integrations/oauth/.well-known/oauth-authorization-server")
async def get_oauth_metadata(request: Request) -> dict:
    """Get OAuth server metadata."""
    # Get base URL
    base_url = str(request.base_url).rstrip("/")
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post", "client_secret_basic"],
        "introspection_endpoint": f"{base_url}/introspect",
        "revocation_endpoint": f"{base_url}/revoke",
        "registration_endpoint": f"{base_url}/register",
        "jwks_uri": f"{base_url}/jwks",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["mcp:read", "mcp:write", "mcp:execute", "offline_access"],
        "service_documentation": f"{base_url}/docs",
    }


