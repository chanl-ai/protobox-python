"""MCP OAuth 2.1 authorization server router."""

from datetime import UTC, datetime
from typing import Any, Optional, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from loguru import logger

from ..auth.dependencies import get_current_user
from ..database.connection import get_database_connection
from ..models.mcp_oauth import (
    MCPOAuthClientCreate,
    MCPOAuthClientResponse,
    OAuthErrorResponse,
    OAuthTokenRequest,
    OAuthTokenResponse,
)
from pydantic import BaseModel, Field
from ..services.mcp_oauth_service import MCPOAuthService

router = APIRouter(tags=["MCP OAuth"])


# Dynamically registered clients are not tied to a workspace. The member who approves
# the consent screen chooses one, and the authorization code is bound to that choice.
UNBOUND_WORKSPACE = ""


async def _is_workspace_member(workspace_id: str, user_id: str) -> bool:
    from bson import ObjectId
    from bson.errors import InvalidId

    from ..database.repositories.team_member_repository import TeamMemberRepository

    try:
        workspace_obj_id = ObjectId(workspace_id)
    except (InvalidId, TypeError):
        return False
    repo = TeamMemberRepository(get_database_connection().database)
    return await repo.get_member_by_workspace_and_user(workspace_obj_id, user_id) is not None


async def resolve_consent_workspace(client: Any, user_id: str, requested_workspace_id: str | None) -> str:
    """Return the workspace an authorization code may be issued for.

    Raises 400 when the choice is missing or conflicts with the client's own workspace,
    and 403 when the user is not a member of the workspace.
    """
    bound = client.workspace_id or UNBOUND_WORKSPACE
    if bound != UNBOUND_WORKSPACE and requested_workspace_id and requested_workspace_id != bound:
        raise HTTPException(status_code=400, detail="This client belongs to a different workspace")
    workspace_id = bound if bound != UNBOUND_WORKSPACE else (requested_workspace_id or "")
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required to authorize this client")
    if not await _is_workspace_member(workspace_id, user_id):
        raise HTTPException(status_code=403, detail="You are not a member of this workspace")
    return workspace_id
basic_auth = HTTPBasic(auto_error=False)


def get_oauth_service() -> MCPOAuthService:
    """Get OAuth service instance."""
    db = get_database_connection()
    return MCPOAuthService(db.database)


def create_error_redirect(redirect_uri: str, error: str, error_description: str = "", state: str = "") -> str:
    """Create error redirect URL."""
    params = {"error": error}
    if error_description:
        params["error_description"] = error_description
    if state:
        params["state"] = state
    return f"{redirect_uri}?{urlencode(params)}"


# HTML generation removed - using client OAuth pages instead


# ==================== OAuth Discovery Endpoints ====================

@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata() -> JSONResponse:
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    oauth_service = get_oauth_service()
    return JSONResponse(content=oauth_service.get_authorization_server_metadata())


@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata() -> JSONResponse:
    """OAuth 2.0 Protected Resource Metadata."""
    oauth_service = get_oauth_service()
    return JSONResponse(content=oauth_service.get_resource_metadata())


# ==================== Authorization Endpoint ====================

@router.get("/authorize", response_model=None)
async def authorize_get(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(""),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
):
    """OAuth authorization endpoint - show login or consent screen."""
    
    # Try to get current user (might not be authenticated yet)
    try:
        from ..auth.dependencies import get_current_user_jwt
        from fastapi import Depends
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        
        # Try to get auth header
        security = HTTPBearer(auto_error=False)
        credentials = await security(request)
        
        if credentials:
            try:
                user = await get_current_user_jwt(credentials)
            except:
                user = None
        else:
            user = None
    except:
        user = None
    
    # Get OAuth service and client info
    oauth_service = get_oauth_service()
    client = await oauth_service.get_client(client_id)
    
    if not client:
        # Invalid client - return error
        return RedirectResponse(
            create_error_redirect(
                redirect_uri,
                "invalid_request",
                "Invalid client_id",
                state,
            )
        )
    
    # Check if in test mode
    from ..config import settings
    
    if not user:
        # User not authenticated - redirect to client login page with OAuth params
        # The client will handle login and redirect back here
        client_url = settings.frontend_url or "http://localhost:3010"
        
        # Encode the OAuth request parameters to pass to the client
        oauth_params = urlencode({
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        })
        
        # Redirect to client OAuth login page
        return RedirectResponse(
            f"{client_url}/oauth/authorize?{oauth_params}",
            status_code=302
        )
    
    # Validate response_type
    if response_type != "code":
        return RedirectResponse(
            create_error_redirect(
                redirect_uri,
                "unsupported_response_type",
                "Only 'code' response type is supported",
                state,
            )
        )
    
    # Validate code_challenge_method
    if code_challenge_method != "S256":
        return RedirectResponse(
            create_error_redirect(
                redirect_uri,
                "invalid_request",
                "Only S256 code challenge method is supported",
                state,
            )
        )
    
    # Get OAuth service
    oauth_service = get_oauth_service()
    
    # Validate client
    client = await oauth_service.get_client(client_id)
    if not client or client.status != "active":
        return RedirectResponse(
            create_error_redirect(
                redirect_uri,
                "invalid_client",
                "Client not found or inactive",
                state,
            )
        )
    
    # Validate redirect_uri
    if redirect_uri not in client.redirect_uris:
        # For security, don't redirect to untrusted URI
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    
    # Validate scopes - if no scopes requested, use client's allowed scopes
    requested_scopes = scope.split() if scope.strip() else client.allowed_scopes
    effective_scope = " ".join(requested_scopes) if requested_scopes else " ".join(client.allowed_scopes)
    
    for requested_scope in requested_scopes:
        if requested_scope not in client.allowed_scopes and requested_scope != "offline_access":
            return RedirectResponse(
                create_error_redirect(
                    redirect_uri,
                    "invalid_scope",
                    f"Invalid scope: {requested_scope}",
                    state,
                )
            )
    
    # Check if user owns the client (auto-approve for client owner)
    if client.user_id == user.id:
        # Auto-approve for client owner - they already consented by creating the client,
        # but only while they are still a member of the client's workspace.
        if not client.workspace_id or not await _is_workspace_member(client.workspace_id, user.id):
            return RedirectResponse(
                create_error_redirect(redirect_uri, "access_denied", "Not a member of this workspace", state)
            )
        try:
            code = await oauth_service.create_authorization_code(
                client_id=client_id,
                user_id=client.user_id,  # Use the client owner's ID
                workspace_id=client.workspace_id,
                redirect_uri=redirect_uri,
                scope=effective_scope,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                state=state,
                ip_address=request.client.host if request.client else None,
            )
            
            # Redirect with authorization code
            params = {"code": code}
            if state:
                params["state"] = state
            return RedirectResponse(f"{redirect_uri}?{urlencode(params)}")
            
        except Exception as e:
            logger.error(f"Error creating authorization code: {e}")
            return RedirectResponse(
                create_error_redirect(
                    redirect_uri,
                    "server_error",
                    "Failed to create authorization code",
                    state,
                )
            )
    
    # User is authenticated but not the client owner - redirect to consent page
    # In production, this would show a consent screen
    # For now, deny access for non-owners
    return RedirectResponse(
        create_error_redirect(
            redirect_uri,
            "access_denied",
            "User is not the client owner",
            state,
        )
    )


@router.post("/authorize/confirm", response_model=None)
async def authorize_post(
    request: Request,
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(""),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    workspace_id: Optional[str] = Query(None),
    user = Depends(get_current_user),
):
    """OAuth authorization endpoint - handle consent confirmation."""
    
    if not user:
        # User not authenticated - show login required error
        return RedirectResponse(
            create_error_redirect(
                redirect_uri,
                "login_required",
                "User authentication required",
                state,
            )
        )
    
    oauth_service = get_oauth_service()
    
    # Validate client again
    client = await oauth_service.get_client(client_id)
    if not client or client.status != "active":
        return RedirectResponse(
            create_error_redirect(
                redirect_uri,
                "invalid_client",
                "Client not found or inactive",
                state,
            )
        )
    
    # Validate scopes - if no scopes requested, use client's allowed scopes
    requested_scopes = scope.split() if scope.strip() else client.allowed_scopes
    effective_scope = " ".join(requested_scopes) if requested_scopes else " ".join(client.allowed_scopes)
    
    for requested_scope in requested_scopes:
        if requested_scope not in client.allowed_scopes:
            return RedirectResponse(
                create_error_redirect(
                    redirect_uri,
                    "invalid_scope",
                    f"Invalid scope: {requested_scope}",
                    state,
                )
            )
    
    authorized_workspace_id = await resolve_consent_workspace(client, user.id, workspace_id)

    try:
        # Create authorization code
        code = await oauth_service.create_authorization_code(
            client_id=client_id,
            user_id=user.id,
            workspace_id=authorized_workspace_id,
            redirect_uri=redirect_uri,
            scope=effective_scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            ip_address=request.client.host if request.client else None,
        )
        
        # Redirect with authorization code
        params = {"code": code}
        if state:
            params["state"] = state
        return RedirectResponse(f"{redirect_uri}?{urlencode(params)}")
        
    except Exception as e:
        logger.error(f"Error creating authorization code: {e}")
        return RedirectResponse(
            create_error_redirect(
                redirect_uri,
                "server_error",
                "Failed to create authorization code",
                state,
            )
        )


@router.post("/authorize/consent", response_model=dict)
async def authorize_consent(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    state: str = Query(""),
    workspace_id: Optional[str] = Query(None),
    user = Depends(get_current_user),
):
    """OAuth consent endpoint - returns JSON for frontend integration."""

    if not user:
        logger.error("OAuth consent failed: User not authenticated")
        raise HTTPException(status_code=401, detail="Authentication required")
    
    oauth_service = get_oauth_service()
    
    # Validate client
    client = await oauth_service.get_client(client_id)
    if not client:
        logger.error(f"OAuth consent failed: Client not found - {client_id}")
        raise HTTPException(status_code=400, detail="Client not found or inactive")
    
    if client.status != "active":
        logger.error(f"OAuth consent failed: Client inactive - {client_id}, status: {client.status}")
        raise HTTPException(status_code=400, detail="Client not found or inactive")
    
    # Validate redirect URI
    if redirect_uri not in client.redirect_uris:
        logger.error(f"OAuth consent failed: Invalid redirect URI - {redirect_uri}")
        raise HTTPException(status_code=400, detail="Invalid redirect URI")
    
    # Validate scopes - if no scopes requested, use client's allowed scopes
    requested_scopes = scope.split() if scope.strip() else client.allowed_scopes
    effective_scope = " ".join(requested_scopes) if requested_scopes else " ".join(client.allowed_scopes)
    
    logger.debug(f"Validating scopes for client {client_id}: requested={scope.split() if scope.strip() else []}, effective={requested_scopes}, allowed={client.allowed_scopes}")
    
    for requested_scope in requested_scopes:
        if requested_scope not in client.allowed_scopes:
            logger.error(f"OAuth consent failed: Invalid scope - {requested_scope}")
            raise HTTPException(status_code=400, detail=f"Invalid scope: {requested_scope}")
    
    authorized_workspace_id = await resolve_consent_workspace(client, user.id, workspace_id)

    try:
        # Create authorization code (pass client object to avoid duplicate database call)
        code = await oauth_service.create_authorization_code(
            client_id=client_id,
            user_id=user.id,
            workspace_id=authorized_workspace_id,
            redirect_uri=redirect_uri,
            scope=effective_scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            ip_address=request.client.host if request.client else None,
            client=client,
        )
        
        # Return redirect URL with authorization code for frontend to handle
        params = {"code": code}
        if state:
            params["state"] = state
            
        redirect_url = f"{redirect_uri}?{urlencode(params)}"
        
        return {
            "success": True,
            "redirect_uri": redirect_url,
            "code": code,
            "state": state
        }        
    except Exception as e:
        logger.error(f"Error creating authorization code: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create authorization code: {str(e)}")


# ==================== Token Endpoint ====================

@router.post("/token", response_model=OAuthTokenResponse)
async def token_exchange(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    code_verifier: str = Form(None),
    refresh_token: str = Form(None),
    scope: str = Form(None),
    client_id: str = Form(None),
    client_secret: str = Form(None),
    credentials: HTTPBasicCredentials | None = Depends(basic_auth),
) -> OAuthTokenResponse | JSONResponse:
    """OAuth token exchange endpoint."""
    
    oauth_service = get_oauth_service()
    
    # Extract client credentials (support both methods)
    if credentials:
        # HTTP Basic Authentication
        client_id = credentials.username
        client_secret = credentials.password
    
    # Check if client_id is provided
    if not client_id:
        return JSONResponse(
            status_code=401,
            content=OAuthErrorResponse(
                error="invalid_client",
                error_description="Client ID required",
            ).model_dump(),
        )
    
    # Get client to check if it's public or confidential
    client = await oauth_service.get_client(client_id)
    if not client:
        return JSONResponse(
            status_code=401,
            content=OAuthErrorResponse(
                error="invalid_client",
                error_description="Client not found",
            ).model_dump(),
        )
    
    # For public clients, we don't require client_secret but do require PKCE
    if client.client_type == "public":
        # Public client - PKCE required for authorization code flow
        if grant_type == "authorization_code" and not code_verifier:
            return JSONResponse(
                status_code=400,
                content=OAuthErrorResponse(
                    error="invalid_request",
                    error_description="PKCE code_verifier required for public clients",
                ).model_dump(),
            )
    else:
        # Confidential client - requires client_secret
        if not client_secret:
            return JSONResponse(
                status_code=401,
                content=OAuthErrorResponse(
                    error="invalid_client",
                    error_description="Client authentication required for confidential clients",
                ).model_dump(),
            )
        
        if not await oauth_service.validate_client_secret(client_id, client_secret):
            return JSONResponse(
                status_code=401,
                content=OAuthErrorResponse(
                    error="invalid_client",
                    error_description="Invalid client credentials",
            ).model_dump(),
        )
    
    # Handle authorization_code grant
    if grant_type == "authorization_code":
        if not code:
            return JSONResponse(
                status_code=400,
                content=OAuthErrorResponse(
                    error="invalid_request",
                    error_description="Missing authorization code",
                ).model_dump(),
            )
        
        # Public clients require code_verifier
        if client.client_type == "public" and not code_verifier:
            return JSONResponse(
                status_code=400,
                content=OAuthErrorResponse(
                    error="invalid_request",
                    error_description="Missing code_verifier for public client",
                ).model_dump(),
            )
        
        # Validate authorization code
        auth_code = await oauth_service.validate_authorization_code(
            code=code,
            client_id=client_id,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )
        
        if not auth_code:
            return JSONResponse(
                status_code=400,
                content=OAuthErrorResponse(
                    error="invalid_grant",
                    error_description="Invalid or expired authorization code",
                ).model_dump(),
            )
        
        # Create tokens
        return await oauth_service.create_tokens(
            client_id=client_id,
            user_id=auth_code.user_id,
            workspace_id=auth_code.workspace_id,
            scope=auth_code.scope,
            ip_address=request.client.host if request.client else None,
        )
    
    # Handle refresh_token grant
    elif grant_type == "refresh_token":
        if not refresh_token:
            return JSONResponse(
                status_code=400,
                content=OAuthErrorResponse(
                    error="invalid_request",
                    error_description="Missing refresh_token",
                ).model_dump(),
            )
        
        # Refresh tokens
        tokens = await oauth_service.refresh_tokens(
            refresh_token=refresh_token,
            client_id=client_id,
            scope=scope,
            ip_address=request.client.host if request.client else None,
        )
        
        if not tokens:
            return JSONResponse(
                status_code=400,
                content=OAuthErrorResponse(
                    error="invalid_grant",
                    error_description="Invalid or expired refresh token",
                ).model_dump(),
            )
        
        return tokens
    
    else:
        return JSONResponse(
            status_code=400,
            content=OAuthErrorResponse(
                error="unsupported_grant_type",
                error_description=f"Grant type '{grant_type}' is not supported",
            ).model_dump(),
        )


# ==================== Token Management Endpoints ====================

@router.post("/revoke")
async def revoke_token(
    token: str = Form(...),
    token_type_hint: str = Form(None),
    client_id: str = Form(None),
    client_secret: str = Form(None),
    credentials: HTTPBasicCredentials | None = Depends(basic_auth),
) -> Response:
    """OAuth token revocation endpoint (RFC 7009)."""
    
    oauth_service = get_oauth_service()
    
    # Extract client credentials
    if credentials:
        client_id = credentials.username
        client_secret = credentials.password
    
    # Client authentication is optional for revocation
    if client_id and client_secret:
        if not await oauth_service.validate_client_secret(client_id, client_secret):
            return Response(status_code=401)
    
    # Revoke the token (always returns 200 per spec)
    await oauth_service.revoke_token(token, token_type_hint)
    return Response(status_code=200)


@router.post("/introspect")
async def introspect_token(
    token: str = Form(...),
    token_type_hint: str = Form(None),
    client_id: str = Form(None),
    client_secret: str = Form(None),
    credentials: HTTPBasicCredentials | None = Depends(basic_auth),
) -> JSONResponse:
    """OAuth token introspection endpoint (RFC 7662)."""
    
    oauth_service = get_oauth_service()
    
    # Extract client credentials
    if credentials:
        client_id = credentials.username
        client_secret = credentials.password
    elif not client_id or not client_secret:
        return JSONResponse(
            status_code=401,
            content={"error": "Client authentication required"},
        )
    
    # Validate client credentials
    if not await oauth_service.validate_client_secret(client_id, client_secret):
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid client credentials"},
        )
    
    # Validate token
    claims = await oauth_service.validate_access_token(token)
    
    if claims:
        return JSONResponse(content={
            "active": True,
            "scope": claims["scope"],
            "client_id": claims["client_id"],
            "username": claims["user_id"],
            "exp": claims.get("expires_at"),
        })
    else:
        return JSONResponse(content={"active": False})


# ==================== Client Management Endpoints (Protected) ====================

@router.post("/clients", response_model=MCPOAuthClientResponse)
async def create_client(
    client_data: MCPOAuthClientCreate,
    user = Depends(get_current_user),
) -> MCPOAuthClientResponse:
    """Create a new OAuth client for the user's workspace."""
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    oauth_service = get_oauth_service()
    
    # Get user's workspace
    workspace_id = user.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="User must have a workspace")
    
    # Create client
    return await oauth_service.create_client(
        workspace_id=workspace_id,
        user_id=user.id,
        client_data=client_data,
    )


@router.get("/clients")
async def list_clients(
    user = Depends(get_current_user),
    show_all: bool = Query(False, description="Show all workspace clients (admin only)"),
) -> list[dict[str, Any]]:
    """List OAuth clients for the current user."""
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    oauth_service = get_oauth_service()
    
    # Get user's workspace
    workspace_id = user.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="User must have a workspace")
    
    # By default, only show user's own clients
    # Admins can see all with show_all=true (future enhancement)
    user_id = user.id if not show_all else None
    
    # List clients (don't expose secrets)
    clients = await oauth_service.list_clients(workspace_id, user_id=user_id)
    return [
        {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "owner_id": client.user_id,  # Show who owns the client
            "is_mine": client.user_id == user.id,  # Flag if current user owns it
            "redirect_uris": client.redirect_uris,
            "allowed_scopes": client.allowed_scopes,
            "created_at": client.created_at,
            "last_used_at": client.last_used_at,
            "status": client.status,
        }
        for client in clients
    ]


@router.delete("/clients/{client_id}")
async def revoke_client(
    client_id: str,
    user = Depends(get_current_user),
) -> JSONResponse:
    """Revoke an OAuth client (only by the owner)."""
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    oauth_service = get_oauth_service()
    
    # Get user's workspace
    workspace_id = user.workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="User must have a workspace")
    
    # Revoke client - user can only revoke their own clients
    if await oauth_service.revoke_client(client_id, workspace_id, user.id):
        return JSONResponse(content={"message": "Client revoked successfully"})
    else:
        raise HTTPException(
            status_code=404, 
            detail="Client not found or you don't have permission to revoke it"
        )


# ==================== Dynamic Client Registration (RFC 7591) ====================

class DynamicClientRegistrationRequest(BaseModel):
    """RFC 7591 compliant dynamic client registration request."""
    client_name: str
    redirect_uris: list[str] = []
    grant_types: list[str] = Field(default_factory=lambda: ["authorization_code", "refresh_token"])
    response_types: list[str] = Field(default_factory=lambda: ["code"])
    scope: str = "mcp:read mcp:execute"
    token_endpoint_auth_method: str = "none"  # Default to public client
    client_type: Optional[Literal["public", "confidential"]] = None  # Optional: "public" or "confidential"

@router.post("/register", response_model=dict)
async def dynamic_client_registration(
    request: Request,
    client_req: DynamicClientRegistrationRequest,
):
    """Dynamic client registration endpoint (RFC 7591) for FastMCP and other clients.
    
    This endpoint allows clients to register themselves without prior authentication.
    Creates a public client (no client_secret) suitable for PKCE flow.
    """
    
    oauth_service = get_oauth_service()
    
    # For dynamic registration, we create a temporary workspace
    # In production, you might want to require some form of initial authentication
    # or use rate limiting to prevent abuse
    
    # Set client_type if provided, otherwise determine based on auth method
    client_type = (
        client_req.client_type
        if client_req.client_type
        else (
            # If token_endpoint_auth_method is not "none", create a confidential client
            "confidential"
            if client_req.token_endpoint_auth_method != "none"
            else "public"
        )
    )
    
    # Create client for FastMCP or Claude Custom Connector
    client_data = MCPOAuthClientCreate(
        client_name=client_req.client_name,
        redirect_uris=client_req.redirect_uris if client_req.redirect_uris else ["http://localhost:8765/callback"],
        client_type=client_type,
        scopes=client_req.scope.split(" ") if isinstance(client_req.scope, str) else ["mcp:read", "mcp:execute"],
    )
    
    # Create the client
    client_response = await oauth_service.create_client(
        workspace_id=UNBOUND_WORKSPACE,
        user_id="",
        client_data=client_data,
    )
    
    # Return RFC 7591 compliant response
    response = {
        "client_id": client_response.client_id,
        "client_name": client_response.client_name,
        "redirect_uris": client_response.redirect_uris,
        "grant_types": client_req.grant_types,
        "response_types": client_req.response_types,
        "scope": client_req.scope,
        "token_endpoint_auth_method": client_req.token_endpoint_auth_method,
        "client_id_issued_at": int(datetime.now(UTC).timestamp()),
    }
    
    # Include client_secret for confidential clients
    if client_type == "confidential" and hasattr(client_response, 'client_secret'):
        response["client_secret"] = client_response.client_secret
        response["client_secret_expires_at"] = 0  # Never expires
    else:
        response["client_secret_expires_at"] = 0  # Public client, no secret
    
    return response


# ==================== JWKS Endpoint ====================

@router.get("/jwks")
async def jwks() -> JSONResponse:
    """
    JSON Web Key Set endpoint for token verification.
    
    Returns public keys used to verify JWT signatures.
    This is a stub implementation - in production, you would:
    1. Generate RSA/EC key pairs for token signing
    2. Return the public keys in JWK format
    3. Rotate keys periodically for security
    """
    # Stub JWKS response
    # In production, this would contain actual public keys
    return JSONResponse(content={
        "keys": [
            {
                "kty": "RSA",  # Key type
                "use": "sig",  # Key use: signature
                "kid": "2024-01-stub",  # Key ID
                "alg": "RS256",  # Algorithm
                "n": "stub_modulus",  # RSA modulus (base64url)
                "e": "AQAB",  # RSA exponent (base64url)
            }
        ]
    })