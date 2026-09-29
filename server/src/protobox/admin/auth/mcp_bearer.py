"""Bearer token authentication provider for MCP endpoints."""

import hashlib
from datetime import datetime
from typing import Any

from loguru import logger
import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from pydantic import BaseModel


# Security scheme for OpenAPI docs
bearer_scheme = HTTPBearer(auto_error=False)


class TokenClaims(BaseModel):
    """Standard JWT token claims with ProtoBox extensions."""

    sub: str  # Subject (user or service ID)
    aud: str | list[str]  # Audience
    iss: str  # Issuer
    exp: int  # Expiration time
    iat: int  # Issued at
    scope: str | None = ""  # Space-separated scopes
    azp: str | None = None  # Authorized party (client ID)
    
    # ProtoBox-specific claims
    workspace_id: str | None = None  # Workspace ID for tenant isolation
    uid: str | None = None  # User ID (alternative to sub)
    email: str | None = None  # User email
    role: str | None = None  # User role
    permissions: list[str] | None = None  # User permissions

    @property
    def scopes(self) -> list[str]:
        """Get scopes as a list."""
        return self.scope.split() if self.scope else []

    def has_scope(self, required_scope: str) -> bool:
        """Check if token has a specific scope."""
        return required_scope in self.scopes

    @property
    def user_id(self) -> str:
        """Get user ID from either sub or uid field."""
        return self.sub or self.uid or ""


class BearerAuthProvider:
    """
    Bearer token authentication provider for MCP.

    Supports:
    - JWT validation with JWKS
    - Multiple issuers (Auth0, Azure AD, Google, etc.)
    - Scope-based authorization
    - Token caching for performance
    """

    def __init__(
        self,
        issuer: str | None = None,
        audience: str | None = None,
        jwks_uri: str | None = None,
        required_scopes: list[str] | None = None,
        cache_ttl: int = 3600,  # Cache JWKS for 1 hour
        validate_audience: bool = True,
    ):
        """
        Initialize bearer auth provider.

        Args:
            issuer: Token issuer URL (e.g., https://auth.example.com)
            audience: Expected audience (e.g., https://api.example.com)
            jwks_uri: JWKS endpoint URL (auto-discovered if not provided)
            required_scopes: List of required scopes for all requests
            cache_ttl: JWKS cache TTL in seconds
            validate_audience: Whether to validate audience claim
        """
        self.issuer = issuer
        self.audience = audience
        self.jwks_uri = jwks_uri
        self.required_scopes = required_scopes or []
        self.cache_ttl = cache_ttl
        self.validate_audience = validate_audience

        # Cache for JWKS keys
        self._keys_cache = None
        self._keys_cache_time = None

        # Cache for validated tokens (to avoid re-validation)
        self._token_cache = {}

    async def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JWKS keys from issuer."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Discover JWKS URI if not provided
                if not self.jwks_uri and self.issuer:
                    try:
                        # Try OpenID Connect discovery
                        metadata_url = f"{self.issuer}/.well-known/openid-configuration"
                        response = await client.get(metadata_url)
                        response.raise_for_status()
                        metadata = response.json()
                        self.jwks_uri = metadata.get("jwks_uri")
                    except Exception as e:
                        logger.warning(f"Failed to discover JWKS URI: {e}")
                        # Fallback to common JWKS path
                        self.jwks_uri = f"{self.issuer}/.well-known/jwks.json"

                if not self.jwks_uri:
                    raise ValueError("JWKS URI not provided and could not be discovered")

                # Fetch JWKS keys
                response = await client.get(self.jwks_uri)
                response.raise_for_status()
                jwks_data = response.json()

                # Cache the keys
                self._keys_cache = jwks_data.get("keys", [])
                self._keys_cache_time = datetime.utcnow()

                return jwks_data

        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch authentication keys")

    async def _get_signing_key(self, token: str) -> dict | None:
        """Get the signing key for a token."""
        # Check if we need to refresh the cache
        if (
            not self._keys_cache
            or not self._keys_cache_time
            or (datetime.utcnow() - self._keys_cache_time).seconds > self.cache_ttl
        ):
            await self._fetch_jwks()

        # Decode token header to get kid
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            alg = unverified_header.get("alg", "RS256")
        except Exception as e:
            logger.error(f"Failed to decode token header: {e}")
            return None

        # Find matching key
        for key in self._keys_cache:
            if kid and key.get("kid") != kid:
                continue
            if key.get("use") == "sig" and key.get("alg", alg) == alg:
                return key

        # If no key found, try refreshing cache once
        if self._keys_cache_time and (datetime.utcnow() - self._keys_cache_time).seconds > 60:
            await self._fetch_jwks()
            for key in self._keys_cache:
                if kid and key.get("kid") != kid:
                    continue
                if key.get("use") == "sig" and key.get("alg", alg) == alg:
                    return key

        return None

    async def validate_token(self, token: str) -> TokenClaims:
        """
        Validate JWT token and return claims.

        Args:
            token: JWT token string

        Returns:
            TokenClaims object with validated claims

        Raises:
            HTTPException: If token is invalid
        """
        # Check token cache first
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        if token_hash in self._token_cache:
            cached_claims, cache_time = self._token_cache[token_hash]
            # Check if cached token is still valid (cache for 5 minutes)
            if (datetime.utcnow() - cache_time).seconds < 300:
                return cached_claims

        try:
            # Get signing key
            signing_key = await self._get_signing_key(token)
            if not signing_key:
                raise HTTPException(status_code=401, detail="No valid signing key found for token")

            # Convert JWK to PEM for jose
            key = jwk.construct(signing_key)

            # Prepare validation options
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "require_exp": True,
                "require_iat": True,
            }

            # Add audience validation if configured
            if self.validate_audience and self.audience:
                options["verify_aud"] = True
                audience = self.audience
            else:
                audience = None

            # Add issuer validation if configured
            if self.issuer:
                options["verify_iss"] = True
                issuer = self.issuer
            else:
                issuer = None

            # Decode and validate token
            payload = jwt.decode(
                token,
                key,
                algorithms=[signing_key.get("alg", "RS256")],
                audience=audience,
                issuer=issuer,
                options=options,
            )

            # Create claims object
            claims = TokenClaims(**payload)

            # Validate required scopes
            for required_scope in self.required_scopes:
                if not claims.has_scope(required_scope):
                    raise HTTPException(
                        status_code=403, detail=f"Missing required scope: {required_scope}"
                    )

            # Cache the validated token
            self._token_cache[token_hash] = (claims, datetime.utcnow())

            # Clean up old cache entries (keep max 100 entries)
            if len(self._token_cache) > 100:
                # Remove oldest entries
                sorted_cache = sorted(self._token_cache.items(), key=lambda x: x[1][1])
                self._token_cache = dict(sorted_cache[-50:])

            return claims

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            raise HTTPException(status_code=500, detail="Token validation failed")

    async def __call__(
        self, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
    ) -> TokenClaims | None:
        """
        FastAPI dependency for bearer token validation.

        Usage:
            @router.get("/protected")
            async def protected_endpoint(
                auth: TokenClaims = Depends(bearer_auth_provider)
            ):
                return {"user": auth.sub}
        """
        if not credentials:
            return None

        return await self.validate_token(credentials.credentials)


class MCPBearerAuth:
    """
    MCP-specific bearer authentication with ProtoBox token support.

    Supports both:
    - Standard JWT bearer tokens
    - ProtoBox MCP tokens (pb_mcp_*)
    """

    def __init__(
        self,
        bearer_provider: BearerAuthProvider | None = None,
        allow_mcp_tokens: bool = True,
        required_scopes: list[str] | None = None,
    ):
        """
        Initialize MCP bearer auth.

        Args:
            bearer_provider: Bearer token validator
            allow_mcp_tokens: Allow ProtoBox MCP tokens
            required_scopes: Required scopes for access
        """
        self.bearer_provider = bearer_provider
        self.allow_mcp_tokens = allow_mcp_tokens
        self.required_scopes = required_scopes or []

    async def validate(
        self, request: Request, workspace_id: str, token: str | None = None
    ) -> dict[str, Any]:
        """
        Validate MCP authentication.

        Supports:
        - Bearer token in Authorization header (JWT, OAuth, or MCP tokens)
        - MCP token in query parameter
        - ProtoBox API keys (legacy)

        Returns:
            Dict with auth info including user_id, scopes, etc.
        """
        # Try Authorization header first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            bearer_token = auth_header[7:]

            # Check if it's a ProtoBox MCP token
            if bearer_token.startswith("pb_mcp_") and self.allow_mcp_tokens:
                return await self._validate_mcp_token(bearer_token, workspace_id)
            
            # Check if it's an OAuth access token
            if bearer_token.startswith("mcp_oauth_"):
                return await self._validate_oauth_token(bearer_token)

            # Validate as JWT using our existing Firebase auth
            # Instead of using bearer_provider with JWKS, use our existing JWT validation
            from .jwt_auth import get_jwt_auth
            jwt_auth = get_jwt_auth()
            
            try:
                jwt_claims = await jwt_auth.validate_jwt_token(bearer_token)
                if jwt_claims:
                    # Map JWT scopes to MCP scopes
                    jwt_scopes = []
                    if jwt_claims.email:  # Authenticated user has basic access
                        jwt_scopes = ["mcp:read", "mcp:execute", "mcp:write"]
                    
                    return {
                        "type": "jwt",
                        "user_id": jwt_claims.sub or jwt_claims.uid,
                        "workspace_id": jwt_claims.workspace_id or workspace_id,
                        "scopes": jwt_scopes,
                        "email": jwt_claims.email,
                    }
            except Exception as e:
                logger.debug(f"JWT validation failed: {e}")

        # Try query parameter token
        if token:
            if token.startswith("pb_mcp_") and self.allow_mcp_tokens:
                return await self._validate_mcp_token(token, workspace_id)
            
            # Check if it's an OAuth access token
            if token.startswith("mcp_oauth_"):
                return await self._validate_oauth_token(token)

            # Try as JWT using our existing auth
            from .jwt_auth import get_jwt_auth
            jwt_auth = get_jwt_auth()
            
            try:
                jwt_claims = await jwt_auth.validate_jwt_token(token)
                if jwt_claims:
                    # Map JWT scopes to MCP scopes
                    jwt_scopes = []
                    if jwt_claims.email:  # Authenticated user has basic access
                        jwt_scopes = ["mcp:read", "mcp:execute", "mcp:write"]
                    
                    return {
                        "type": "jwt",
                        "user_id": jwt_claims.sub or jwt_claims.uid,
                        "workspace_id": jwt_claims.workspace_id or workspace_id,
                        "scopes": jwt_scopes,
                        "email": jwt_claims.email,
                    }
            except Exception as e:
                logger.debug(f"JWT validation failed: {e}")

        # No valid authentication found
        raise HTTPException(
            status_code=401, detail="Authentication required. Provide Bearer token or MCP token."
        )

    async def _validate_mcp_token(self, token: str, workspace_id: str) -> dict[str, Any]:
        """Validate ProtoBox MCP token."""
        from ..database.connection import get_database_connection
        from .mcp_auth import MCPAuthService

        db = get_database_connection()
        token_info = await MCPAuthService.validate_token(db.database, token, workspace_id)

        if not token_info:
            raise HTTPException(status_code=401, detail="Invalid or expired MCP token")

        # Check required scopes
        token_scopes = token_info.get("scopes", [])
        for required_scope in self.required_scopes:
            if required_scope not in token_scopes:
                raise HTTPException(
                    status_code=403, detail=f"Missing required scope: {required_scope}"
                )

        return {
            "type": "mcp_token",
            "token_id": token_info["token_id"],
            "workspace_id": token_info["workspace_id"],
            "scopes": token_scopes,
            "rate_limit": token_info.get("rate_limit", 100),
        }

    async def _validate_mcp_token_any_workspace(self, token: str) -> dict[str, Any]:
        """Validate ProtoBox MCP token without requiring workspace_id upfront."""
        from ..database.connection import get_database_connection
        from .mcp_auth import MCPAuthService

        db = get_database_connection()
        token_info = await MCPAuthService.validate_token_any_workspace(db.database, token)

        if not token_info:
            raise HTTPException(status_code=401, detail="Invalid or expired MCP token")

        # Check required scopes
        token_scopes = token_info.get("scopes", [])
        for required_scope in self.required_scopes:
            if required_scope not in token_scopes:
                raise HTTPException(
                    status_code=403, detail=f"Missing required scope: {required_scope}"
                )

        return {
            "type": "mcp_token",
            "token_id": token_info["token_id"],
            "workspace_id": token_info["workspace_id"],
            "scopes": token_scopes,
            "rate_limit": token_info.get("rate_limit", 100),
        }
    
    async def _validate_oauth_token(self, token: str) -> dict[str, Any]:
        """Validate OAuth access token for MCP endpoints."""
        from ..database.connection import get_database_connection
        from ..services.mcp_oauth_service import MCPOAuthService
        
        db = get_database_connection()
        oauth_service = MCPOAuthService(db.database)
        
        # Validate the OAuth token
        token_claims = await oauth_service.validate_access_token(token)
        
        if not token_claims:
            raise HTTPException(status_code=401, detail="Invalid or expired OAuth token")
        
        # Parse scopes
        token_scopes = token_claims.get("scope", "").split()
        
        # Check required scopes
        for required_scope in self.required_scopes:
            # Map generic scopes to OAuth scopes
            oauth_scope = self._map_to_oauth_scope(required_scope)
            if oauth_scope not in token_scopes:
                raise HTTPException(
                    status_code=403, detail=f"Missing required scope: {oauth_scope}"
                )
        
        return {
            "type": "oauth_token",
            "client_id": token_claims["client_id"],
            "user_id": token_claims["user_id"],
            "workspace_id": token_claims["workspace_id"],
            "scopes": token_scopes,
            "expires_at": token_claims.get("expires_at"),
        }
    
    def _map_to_oauth_scope(self, scope: str) -> str:
        """Map generic scopes to OAuth MCP scopes."""
        # Map common scope patterns to OAuth scopes
        scope_mapping = {
            "read:actions": "mcp:read",
            "execute:actions": "mcp:execute",
            "write:actions": "mcp:write",
            "actions:read": "mcp:read",
            "actions:execute": "mcp:execute",
            "actions:write": "mcp:write",
        }
        return scope_mapping.get(scope, scope)

    async def validate_with_auto_workspace(self, request: Request, token: str | None = None) -> dict[str, Any]:
        """
        Validate MCP authentication and auto-discover workspace from token.
        
        For multitenant endpoints where workspace_id should come from the token itself.
        
        Returns:
            Dict with auth info including user_id, scopes, workspace_id, etc.
        """
        # Try Authorization header first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            bearer_token = auth_header[7:]

            # Check if it's a ProtoBox MCP token
            if bearer_token.startswith("pb_mcp_") and self.allow_mcp_tokens:
                return await self._validate_mcp_token_any_workspace(bearer_token)
            
            # Check if it's an OAuth access token (for MCP endpoints)
            if bearer_token.startswith("mcp_oauth_"):
                return await self._validate_oauth_token(bearer_token)

            # Validate as JWT using our existing Firebase auth
            from .jwt_auth import get_jwt_auth
            jwt_auth = get_jwt_auth()
            
            try:
                jwt_claims = await jwt_auth.validate_jwt_token(bearer_token)
                if jwt_claims:
                    # Extract workspace_id from claims
                    workspace_id = jwt_claims.workspace_id
                    if not workspace_id:
                        raise HTTPException(
                            status_code=400, 
                            detail="JWT token must include workspace_id claim for MCP access"
                        )
                    
                    # Map JWT scopes to MCP scopes
                    jwt_scopes = []
                    if jwt_claims.email:  # Authenticated user has basic access
                        jwt_scopes = ["mcp:read", "mcp:execute", "mcp:write"]
                    
                    return {
                        "type": "jwt",
                        "user_id": jwt_claims.sub or jwt_claims.uid,
                        "workspace_id": workspace_id,
                        "scopes": jwt_scopes,
                        "email": jwt_claims.email,
                    }
            except Exception as e:
                logger.debug(f"JWT validation failed: {e}")

        # Try query parameter token
        if token:
            if token.startswith("pb_mcp_") and self.allow_mcp_tokens:
                return await self._validate_mcp_token_any_workspace(token)
            
            # Check if it's an OAuth access token
            if token.startswith("mcp_oauth_"):
                return await self._validate_oauth_token(token)

            # Try as JWT using our existing auth
            from .jwt_auth import get_jwt_auth
            jwt_auth = get_jwt_auth()
            
            try:
                jwt_claims = await jwt_auth.validate_jwt_token(token)
                if jwt_claims:
                    # Extract workspace_id from claims
                    workspace_id = jwt_claims.workspace_id
                    if not workspace_id:
                        raise HTTPException(
                            status_code=400, 
                            detail="JWT token must include workspace_id claim for MCP access"
                        )
                    
                    # Map JWT scopes to MCP scopes
                    jwt_scopes = []
                    if jwt_claims.email:  # Authenticated user has basic access
                        jwt_scopes = ["mcp:read", "mcp:execute", "mcp:write"]
                    
                    return {
                        "type": "jwt",
                        "user_id": jwt_claims.sub or jwt_claims.uid,
                        "workspace_id": workspace_id,
                        "scopes": jwt_scopes,
                        "email": jwt_claims.email,
                    }
            except Exception as e:
                logger.debug(f"JWT validation failed: {e}")

        # No valid authentication found
        raise HTTPException(
            status_code=401, detail="Authentication required. Provide Bearer token or MCP token."
        )


# Import settings for configuration
from ..config import settings

# Default bearer auth provider for ProtoBox
# We don't use external JWKS validation - we use our existing Firebase JWT validation
# This keeps the auth consistent across all endpoints
default_bearer_provider = None  # We handle JWT validation internally using Firebase auth

# MCP-specific auth with support for:
# - JWT tokens (validated using our Firebase auth)
# - OAuth tokens (for third-party clients)
# - MCP tokens (ProtoBox-specific tokens)
mcp_bearer_auth = MCPBearerAuth(
    bearer_provider=default_bearer_provider,  # Not used since we handle JWT internally
    allow_mcp_tokens=True,
    required_scopes=["read:actions", "execute:actions"],
)
