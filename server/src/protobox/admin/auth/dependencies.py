"""
Authentication dependencies for FastAPI routes.

Provides both JWT and API key authentication middleware.
"""

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from .api_key_auth import APIKeyAuth, get_api_key_auth
from .auth_config import get_auth_config
from .jwt_auth import JWTAuth, get_jwt_auth
from .models import ServiceContext, User
from .service_key_auth import ServiceKeyAuth, get_service_key_auth

# Security schemes
security = HTTPBearer(auto_error=False)


async def get_current_user_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_auth: JWTAuth = Depends(get_jwt_auth),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
) -> User | None:
    """
    Get current user from JWT token.

    Args:
        credentials: Bearer token from request
        jwt_auth: JWT authentication service
        api_key_auth: API key authentication service

    Returns:
        User object if valid, None if invalid
    """
    if not credentials or not credentials.credentials:
        logger.debug("No credentials provided in request")
        return None

    # Always use Firebase authentication - no mode switching
    auth_config = get_auth_config()
    logger.debug(
        f"Firebase auth, Token prefix: {credentials.credentials[:20] if credentials.credentials else 'None'}..."
    )

    try:
        # Firebase JWT validation
        logger.debug("Validating JWT token with Firebase")
        jwt_claims = await jwt_auth.validate_jwt_token(credentials.credentials)

        if not jwt_claims:
            logger.warning("JWT validation failed - invalid or expired token")
            return None

        logger.trace(
            f"JWT validated successfully: uid={jwt_claims.sub}, email={jwt_claims.email}"
        )
        # Create a User object from the JWT data
        # NOTE: We do NOT create users here - that's handled by Next.js platform
        try:
            return User.from_jwt_claims(jwt_claims)
        except ValueError as e:
            logger.error(f"Failed to create User from JWT claims: {e}")
            return None


    except Exception as e:
        logger.error(f"JWT authentication error: {e}")
        return None


async def get_current_user_api_key(
    x_api_key: str | None = Header(None, description="API Key in format 'key_id:secret_key'"),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
) -> User | None:
    """
    Get current user from API key.

    Args:
        x_api_key: API key header
        api_key_auth: API key authentication service

    Returns:
        User object if valid, None if invalid
    """
    if not x_api_key:
        return None

    try:
        # Parse API key (format: key_id:secret_key)
        if ":" not in x_api_key:
            return None

        key_id, secret_key = x_api_key.split(":", 1)

        # Validate API key
        api_key = await api_key_auth.validate_api_key(key_id, secret_key)

        if not api_key:
            return None

        # Get user
        return await api_key_auth.get_user_by_api_key(key_id)


    except Exception as e:
        logger.error(f"API key authentication error: {e}")
        return None


async def get_current_user(
    jwt_user: User | None = Depends(get_current_user_jwt),
    api_key_user: User | None = Depends(get_current_user_api_key),
) -> User | None:
    """
    Get current user from either JWT or API key.

    Args:
        jwt_user: User from JWT token
        api_key_user: User from API key

    Returns:
        User object if authenticated, None if not
    """
    # Prefer JWT token over API key
    if jwt_user:
        return jwt_user

    if api_key_user:
        return api_key_user

    return None


async def require_authentication(current_user: User | None = Depends(get_current_user)) -> User:
    """
    Require authentication (JWT or API key).

    Args:
        current_user: Current user from authentication

    Returns:
        User object

    Raises:
        HTTPException: If not authenticated
    """
    logger.debug(
        f"require_authentication: current_user={current_user.id if current_user else None}"
    )
    if not current_user:
        # Always require authentication with Firebase
        logger.warning("Authentication required but no user found - Firebase auth required")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide either JWT token or API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # CRITICAL: Additional validation to prevent empty ID bypass
    if not current_user.id or current_user.id == "":
        logger.error(f"User has invalid/empty ID: {current_user}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user authentication - missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user


async def require_jwt_authentication(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_auth: JWTAuth = Depends(get_jwt_auth),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
) -> User:
    """
    Require JWT authentication specifically.

    Args:
        credentials: Bearer token from request
        supabase_auth: Supabase authentication service
        api_key_auth: API key authentication service

    Returns:
        User object

    Raises:
        HTTPException: If not authenticated with JWT
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Always use Firebase authentication
    try:
        # Firebase JWT validation
        jwt_claims = await jwt_auth.validate_jwt_token(credentials.credentials)

        if not jwt_claims:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired JWT token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create a User object from the JWT data
        return User.from_jwt_claims(jwt_claims)


    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_api_key_authentication(
    x_api_key: str = Header(..., description="API Key in format 'key_id:secret_key'"),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
) -> User:
    """
    Require API key authentication specifically.

    Args:
        x_api_key: API key header
        api_key_auth: API key authentication service

    Returns:
        User object

    Raises:
        HTTPException: If not authenticated with API key
    """
    try:
        # Parse API key (format: key_id:secret_key)
        if ":" not in x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format. Use 'key_id:secret_key'",
            )

        key_id, secret_key = x_api_key.split(":", 1)

        # Validate API key
        api_key = await api_key_auth.validate_api_key(key_id, secret_key)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired API key"
            )

        # Get user
        user = await api_key_auth.get_user_by_api_key(key_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found for API key"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key authentication failed"
        )


# Service key authentication dependencies
async def get_service_context(
    x_service_key: str | None = Header(None, alias="X-Service-Key"),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
    service_key_auth: ServiceKeyAuth = Depends(get_service_key_auth),
) -> ServiceContext | None:
    """
    Get service context from service API key.

    Args:
        x_service_key: Service API key from header
        service_key_auth: Service key authentication service

    Returns:
        ServiceContext if valid, None if invalid
    """
    if not x_service_key:
        return None

    try:
        # Validate service key
        service_key = await service_key_auth.validate_service_key(x_service_key)

        if not service_key:
            logger.warning("Service key validation failed")
            return None

        # Return service context with optional user ID
        return ServiceContext(
            service_name=service_key.service_name,
            scopes=service_key.scopes,
            key_id=service_key.id,
            user_id=x_user_id,  # Pass through user ID from header
        )

    except Exception as e:
        logger.error(f"Service key authentication error: {e}")
        return None


async def require_service_authentication(
    service_context: ServiceContext | None = Depends(get_service_context),
) -> ServiceContext:
    """
    Require service authentication via service API key.

    Args:
        service_context: Service context from authentication

    Returns:
        ServiceContext object

    Raises:
        HTTPException: If not authenticated
    """
    if not service_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required. Provide X-Service-Key header.",
        )

    return service_context


# Legacy compatibility - map to new auth functions
async def get_current_active_user(current_user: User = Depends(require_authentication)) -> User:
    """
    Legacy compatibility function for existing routes.

    Args:
        current_user: Current authenticated user

    Returns:
        User object
    """
    return current_user
