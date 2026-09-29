"""MCP OAuth 2.1 authorization server service."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..config import settings
from ..models.mcp_oauth import (
    MCPAuthorizationCode,
    MCPOAuthClient,
    MCPOAuthClientCreate,
    MCPOAuthClientResponse,
    MCPOAuthToken,
    OAuthErrorResponse,
    OAuthTokenRequest,
    OAuthTokenResponse,
)


class MCPOAuthService:
    """OAuth 2.1 authorization server for MCP."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """Initialize OAuth service with database connection."""
        self.db = db
        self.clients_collection = db.mcp_oauth_clients
        self.codes_collection = db.mcp_authorization_codes
        self.tokens_collection = db.mcp_oauth_tokens
        
        # Token configuration
        self.access_token_ttl = 3600  # 1 hour
        self.refresh_token_ttl = 2592000  # 30 days
        self.authorization_code_ttl = 600  # 10 minutes
    
    # ==================== Client Management ====================
    
    async def list_workspace_clients(self, workspace_id: str) -> list:
        """List all OAuth clients for a workspace."""
        from ..models.mcp_oauth import MCPOAuthClient
        
        cursor = self.clients_collection.find({
            "workspace_id": workspace_id,
            "status": "active"
        })
        
        clients = []
        async for doc in cursor:
            # Convert ObjectId to string for Pydantic model
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            # Convert MongoDB document to MCPOAuthClient model
            clients.append(MCPOAuthClient(**doc))
        
        return clients
    
    async def create_client_from_model(self, client: Any) -> None:
        """Create a new OAuth client from a model object."""
        # Convert model to dict and insert
        client_dict = client.model_dump() if hasattr(client, 'model_dump') else client.dict()
        await self.clients_collection.insert_one(client_dict)
    
    async def create_client(
        self,
        workspace_id: str,
        user_id: str,
        client_data: MCPOAuthClientCreate
    ) -> MCPOAuthClientResponse:
        """Create a new OAuth client owned by a specific user in a workspace."""
        # Generate client credentials
        client_id = f"mcp_{uuid.uuid4().hex}"
        client_secret = secrets.token_urlsafe(32)
        
        # Hash the secret for storage
        client_secret_hash = bcrypt.hashpw(
            client_secret.encode(), bcrypt.gensalt()
        ).decode()
        
        # Create client model - owned by the creating user
        client = MCPOAuthClient(
            client_id=client_id,
            client_secret_hash=client_secret_hash,
            client_name=client_data.client_name,
            client_type=getattr(client_data, 'client_type', "confidential"),  # Default to confidential
            user_id=user_id,  # Owner of this client
            workspace_id=workspace_id,
            redirect_uris=client_data.redirect_uris,
            allowed_scopes=client_data.scopes,
            description=client_data.description,
            logo_uri=client_data.logo_uri,
            client_uri=client_data.client_uri,
            created_by=user_id,  # Same as user_id for consistency
        )
        
        # Store in database
        await self.clients_collection.insert_one(client.model_dump_for_db())
        
        logger.info(f"Created OAuth client {client_id} for workspace {workspace_id}")
        
        # Return response with plain secret (only time it's shown!)
        return MCPOAuthClientResponse(
            client_id=client_id,
            client_secret=client_secret,
            client_name=client.client_name,
            redirect_uris=client.redirect_uris,
            allowed_scopes=client.allowed_scopes,
            created_at=client.created_at,
        )
    
    async def get_client(self, client_id: str) -> MCPOAuthClient | None:
        """Get OAuth client by ID."""
        doc = await self.clients_collection.find_one({"client_id": client_id})
        if doc:
            # Convert MongoDB ObjectId to string
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            return MCPOAuthClient(**doc)
        return None
    
    async def list_clients(
        self, workspace_id: str, user_id: str | None = None
    ) -> list[MCPOAuthClient]:
        """List OAuth clients for a workspace, optionally filtered by user."""
        query = {"workspace_id": workspace_id, "status": "active"}
        
        # If user_id provided, only show that user's clients
        if user_id:
            query["user_id"] = user_id
        
        cursor = self.clients_collection.find(query)
        clients = []
        async for doc in cursor:
            # Convert MongoDB ObjectId to string
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            clients.append(MCPOAuthClient(**doc))
        return clients
    
    async def revoke_client(
        self, client_id: str, workspace_id: str, user_id: str
    ) -> bool:
        """Revoke an OAuth client (any user in the workspace can revoke)."""
        # Any user in the workspace can revoke OAuth clients
        result = await self.clients_collection.update_one(
            {
                "client_id": client_id,
                "workspace_id": workspace_id,
                # Removed user_id check - any workspace member can revoke
            },
            {"$set": {"status": "revoked", "updated_at": datetime.now(UTC), "revoked_by": user_id}}
        )
        
        if result.modified_count > 0:
            # Also revoke all tokens for this client
            await self.tokens_collection.update_many(
                {"client_id": client_id},
                {"$set": {"revoked": True, "revoked_at": datetime.now(UTC)}}
            )
            logger.info(f"User {user_id} revoked OAuth client {client_id}")
            return True
        return False
    
    async def validate_client_secret(
        self, client_id: str, client_secret: str
    ) -> bool:
        """Validate client credentials."""
        client = await self.get_client(client_id)
        if not client or client.status != "active":
            return False
        
        # Check bcrypt hash
        return bcrypt.checkpw(
            client_secret.encode(),
            client.client_secret_hash.encode()
        )
    
    # ==================== Authorization Flow ====================
    
    async def create_authorization_code(
        self,
        client_id: str,
        user_id: str,
        workspace_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str = "S256",
        state: str | None = None,
        ip_address: str | None = None,
        client: MCPOAuthClient | None = None,
    ) -> str:
        """Create authorization code for OAuth flow."""
        # Use provided client or fetch it
        if client is None:
            client = await self.get_client(client_id)
            if not client or client.status != "active":
                raise ValueError("Invalid client")
        
        # Validate redirect URI
        if redirect_uri not in client.redirect_uris:
            raise ValueError("Invalid redirect URI")
        
        # Validate requested scopes
        requested_scopes = scope.split()
        for requested_scope in requested_scopes:
            if requested_scope not in client.allowed_scopes:
                raise ValueError(f"Invalid scope: {requested_scope}")
        
        # Generate secure authorization code
        code = secrets.token_urlsafe(32)
        
        # Create authorization code model
        auth_code = MCPAuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            workspace_id=workspace_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=datetime.now(UTC) + timedelta(seconds=self.authorization_code_ttl),
            created_from_ip=ip_address,
        )
        
        # Store in database
        await self.codes_collection.insert_one(auth_code.model_dump_for_db())
        
        logger.info(f"Created authorization code for client {client_id}")
        return code
    
    async def validate_authorization_code(
        self,
        code: str,
        client_id: str,
        code_verifier: str,
        redirect_uri: str | None = None,
    ) -> MCPAuthorizationCode | None:
        """Validate authorization code and PKCE."""
        # Find authorization code
        auth_code_doc = await self.codes_collection.find_one({"code": code})
        if not auth_code_doc:
            logger.warning("Authorization code not found")
            return None
        
        # Convert MongoDB ObjectId to string
        if "_id" in auth_code_doc:
            auth_code_doc["_id"] = str(auth_code_doc["_id"])
        
        auth_code = MCPAuthorizationCode(**auth_code_doc)
        
        # Validate code is still valid
        if not auth_code.is_valid:
            logger.warning("Authorization code expired or already used")
            return None
        
        # Validate client ID matches
        if auth_code.client_id != client_id:
            logger.warning("Client ID mismatch")
            return None
        
        # Validate redirect URI if provided
        if redirect_uri and auth_code.redirect_uri != redirect_uri:
            logger.warning("Redirect URI mismatch")
            return None
        
        # Validate PKCE code verifier
        if not self._validate_pkce(
            code_verifier, auth_code.code_challenge, auth_code.code_challenge_method
        ):
            logger.warning("PKCE validation failed")
            return None
        
        # Mark code as used
        await self.codes_collection.update_one(
            {"_id": auth_code_doc["_id"]},
            {"$set": {"used": True, "used_at": datetime.now(UTC)}}
        )
        
        return auth_code
    
    def _validate_pkce(
        self, verifier: str, challenge: str, method: str = "S256"
    ) -> bool:
        """Validate PKCE code challenge."""
        if method != "S256":
            return False  # Only support S256
        
        # Calculate challenge from verifier
        calculated = hashlib.sha256(verifier.encode()).hexdigest()
        
        # Base64url encode without padding
        import base64
        calculated_b64 = base64.urlsafe_b64encode(
            bytes.fromhex(calculated)
        ).rstrip(b"=").decode()
        
        return calculated_b64 == challenge
    
    # ==================== Token Management ====================
    
    async def create_tokens(
        self,
        client_id: str,
        user_id: str,
        workspace_id: str,
        scope: str,
        ip_address: str | None = None,
    ) -> OAuthTokenResponse:
        """Create access and refresh tokens."""
        # Generate tokens
        access_token = f"mcp_oauth_{secrets.token_urlsafe(32)}"
        refresh_token = f"mcp_refresh_{secrets.token_urlsafe(32)}"
        
        # Hash tokens for storage
        access_token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        # Create access token record
        access_token_doc = MCPOAuthToken(
            token_hash=access_token_hash,
            token_type="access",
            client_id=client_id,
            user_id=user_id,
            workspace_id=workspace_id,
            scope=scope,
            expires_at=datetime.now(UTC) + timedelta(seconds=self.access_token_ttl),
            refresh_token_hash=refresh_token_hash,
            created_from_ip=ip_address,
        )
        
        # Create refresh token record
        refresh_token_doc = MCPOAuthToken(
            token_hash=refresh_token_hash,
            token_type="refresh",
            client_id=client_id,
            user_id=user_id,
            workspace_id=workspace_id,
            scope=scope,
            expires_at=datetime.now(UTC) + timedelta(seconds=self.refresh_token_ttl),
            created_from_ip=ip_address,
        )
        
        # Store both tokens
        await self.tokens_collection.insert_many([
            access_token_doc.model_dump_for_db(),
            refresh_token_doc.model_dump_for_db(),
        ])
        
        logger.info(f"Created tokens for client {client_id}")
        
        return OAuthTokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self.access_token_ttl,
            refresh_token=refresh_token,
            scope=scope,
        )
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        client_id: str,
        scope: str | None = None,
        ip_address: str | None = None,
    ) -> OAuthTokenResponse | None:
        """Refresh access token using refresh token."""
        # Hash the refresh token
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        # Find refresh token
        refresh_doc = await self.tokens_collection.find_one({
            "token_hash": refresh_token_hash,
            "token_type": "refresh",
            "client_id": client_id,
        })
        
        if not refresh_doc:
            logger.warning("Refresh token not found")
            return None
        
        # Convert MongoDB ObjectId to string
        if "_id" in refresh_doc:
            refresh_doc["_id"] = str(refresh_doc["_id"])
        
        refresh_token_obj = MCPOAuthToken(**refresh_doc)
        
        # Validate refresh token
        if not refresh_token_obj.is_valid:
            logger.warning("Refresh token expired or revoked")
            return None
        
        # Handle scope reduction if requested
        if scope:
            # Validate requested scopes are subset of original
            original_scopes = set(refresh_token_obj.scope.split())
            requested_scopes = set(scope.split())
            if not requested_scopes.issubset(original_scopes):
                logger.warning("Invalid scope reduction")
                return None
            final_scope = scope
        else:
            final_scope = refresh_token_obj.scope
        
        # Rotate refresh token (security best practice)
        await self.tokens_collection.update_one(
            {"_id": refresh_doc["_id"]},
            {"$set": {"revoked": True, "revoked_at": datetime.now(UTC)}}
        )
        
        # Create new tokens
        return await self.create_tokens(
            client_id=client_id,
            user_id=refresh_token_obj.user_id,
            workspace_id=refresh_token_obj.workspace_id,
            scope=final_scope,
            ip_address=ip_address,
        )
    
    async def validate_access_token(
        self, token: str
    ) -> dict[str, Any] | None:
        """Validate access token and return claims."""
        # Hash the token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Find token
        token_doc = await self.tokens_collection.find_one({
            "token_hash": token_hash,
            "token_type": "access",
        })
        
        if not token_doc:
            return None
        
        # Convert MongoDB ObjectId to string
        if "_id" in token_doc:
            token_doc["_id"] = str(token_doc["_id"])
        
        token_obj = MCPOAuthToken(**token_doc)
        
        # Validate token
        if not token_obj.is_valid:
            return None
        
        # Update usage stats
        await self.tokens_collection.update_one(
            {"_id": token_doc["_id"]},
            {
                "$set": {"last_used_at": datetime.now(UTC)},
                "$inc": {"use_count": 1},
            }
        )
        
        # Return token claims
        return {
            "client_id": token_obj.client_id,
            "user_id": token_obj.user_id,
            "workspace_id": token_obj.workspace_id,
            "scope": token_obj.scope,
            "expires_at": token_obj.expires_at.isoformat() if token_obj.expires_at else None,
        }
    
    async def revoke_token(
        self, token: str, token_type_hint: str | None = None
    ) -> bool:
        """Revoke an access or refresh token."""
        # Hash the token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Build query
        query = {"token_hash": token_hash}
        if token_type_hint in ["access_token", "refresh_token"]:
            query["token_type"] = token_type_hint.replace("_token", "")
        
        # Revoke the token
        result = await self.tokens_collection.update_one(
            query,
            {"$set": {"revoked": True, "revoked_at": datetime.now(UTC)}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Revoked token")
            return True
        return False
    
    # ==================== OAuth Metadata ====================
    
    def get_authorization_server_metadata(self) -> dict[str, Any]:
        """Get OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
        base_url = settings.mcp_server_url or "http://localhost:8090"
        return {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/admin/api/v1/oauth/authorize",
            "token_endpoint": f"{base_url}/admin/api/v1/oauth/token",
            "token_endpoint_auth_methods_supported": [
                "none",  # For public clients with PKCE
                "client_secret_post",
                "client_secret_basic",
            ],
            "introspection_endpoint": f"{base_url}/admin/api/v1/oauth/introspect",
            "revocation_endpoint": f"{base_url}/admin/api/v1/oauth/revoke",
            "registration_endpoint": f"{base_url}/admin/api/v1/oauth/register",  # Dynamic registration
            "jwks_uri": f"{base_url}/admin/api/v1/oauth/jwks",  # JWKS endpoint for token verification
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": [
                "mcp:read",
                "mcp:write",
                "mcp:execute",
                "offline_access",
            ],
            "service_documentation": f"{base_url}/docs",
            "ui_locales_supported": ["en"],
            "claims_supported": ["sub", "iss", "aud", "exp", "iat", "jti", "scope"],
            "request_parameter_supported": False,
            "request_uri_parameter_supported": False,
            "require_request_uri_registration": False,
            "authorization_response_iss_parameter_supported": True,
        }
    
    def get_resource_metadata(self) -> dict[str, Any]:
        """Get OAuth 2.0 Protected Resource Metadata (RFC 8414)."""
        base_url = settings.mcp_server_url or "http://localhost:8090"
        return {
            "resource": f"{base_url}/mcp",
            "authorization_servers": [base_url],
            "bearer_methods_supported": ["header"],
            "scopes_supported": [
                "mcp:read",
                "mcp:write",
                "mcp:execute",
            ],
            "resource_documentation": f"{base_url}/docs#mcp",
        }