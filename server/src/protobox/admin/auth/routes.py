"""
Authentication routes for user signup, login, and API key management.
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel

from .api_key_auth import APIKeyAuth, get_api_key_auth
from .models import APIKeyInfo, CreateAPIKeyRequest, CreateAPIKeyResponse, SupabaseUserInfo, User
from .supabase_auth import SupabaseAuth, get_supabase_auth


# Request/Response models
class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RevokeAPIKeyRequest(BaseModel):
    key_id: str


# Security dependencies
security = HTTPBearer()


async def get_current_user_from_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_auth: SupabaseAuth = Depends(get_supabase_auth),
) -> SupabaseUserInfo:
    """
    Get current user from JWT token.

    Args:
        credentials: Bearer token from request
        supabase_auth: Supabase authentication service

    Returns:
        SupabaseUserInfo object

    Raises:
        HTTPException: If token is invalid
    """
    if not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info = await supabase_auth.validate_jwt_token(credentials.credentials)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_info


async def get_current_user_from_api_key(
    x_api_key: str = Header(..., description="API Key in format 'key_id:secret_key'"),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
) -> User:
    """
    Get current user from API key.

    Args:
        x_api_key: API key header
        api_key_auth: API key authentication service

    Returns:
        User object

    Raises:
        HTTPException: If API key is invalid
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

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format"
        )


# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=dict)
async def signup(request: SignupRequest, supabase_auth: SupabaseAuth = Depends(get_supabase_auth)):
    """
    Sign up a new user with Supabase.

    Args:
        request: Signup request with email and password
        supabase_auth: Supabase authentication service

    Returns:
        Signup response from Supabase
    """
    try:
        result = await supabase_auth.create_user_with_supabase(request.email, request.password)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user. Email might already be registered.",
            )

        logger.info(f"User signed up: {request.email}")
        return {
            "message": "User created successfully",
            "user": result.get("user", {}),
            "session": result.get("session", {}),
        }

    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signup",
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, supabase_auth: SupabaseAuth = Depends(get_supabase_auth)):
    """
    Login user with Supabase.

    Args:
        request: Login request with email and password
        supabase_auth: Supabase authentication service

    Returns:
        Login response with JWT token
    """
    try:
        result = await supabase_auth.authenticate_with_supabase(request.email, request.password)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )

        logger.info(f"User logged in: {request.email}")
        return LoginResponse(
            access_token=result["access_token"],
            token_type="bearer",
            expires_in=result.get("expires_in", 3600),
            user=result.get("user", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )


@router.post("/api-keys", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: SupabaseUserInfo = Depends(get_current_user_from_jwt),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
):
    """
    Create a new API key for the authenticated user.

    Args:
        request: API key creation request
        current_user: Current user from JWT token
        api_key_auth: API key authentication service

    Returns:
        API key response with secret key (only shown once)
    """
    try:
        # Create or get user in MongoDB
        user = await api_key_auth.create_or_get_user(current_user.sub, current_user.email)

        # Create API key
        api_key_response = await api_key_auth.create_api_key(user, request)

        logger.info(f"API key created: {request.name} for {user.email}")
        return api_key_response

    except Exception as e:
        logger.error(f"API key creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create API key"
        )


@router.get("/api-keys", response_model=list[APIKeyInfo])
async def list_api_keys(
    current_user: SupabaseUserInfo = Depends(get_current_user_from_jwt),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
):
    """
    List all API keys for the authenticated user.

    Args:
        current_user: Current user from JWT token
        api_key_auth: API key authentication service

    Returns:
        List of API key information (without secrets)
    """
    try:
        # Get user from MongoDB
        user = await api_key_auth.create_or_get_user(current_user.sub, current_user.email)

        # Get API keys
        return await api_key_auth.get_user_api_keys(user.id)


    except Exception as e:
        logger.error(f"API key listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list API keys"
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: SupabaseUserInfo = Depends(get_current_user_from_jwt),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
):
    """
    Revoke an API key.

    Args:
        key_id: API key ID to revoke
        current_user: Current user from JWT token
        api_key_auth: API key authentication service

    Returns:
        Success message
    """
    try:
        # Get user from MongoDB
        user = await api_key_auth.create_or_get_user(current_user.sub, current_user.email)

        # Revoke API key
        success = await api_key_auth.revoke_api_key(user.id, key_id)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

        logger.info(f"API key revoked: {key_id}")
        return {"message": "API key revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key revocation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke API key"
        )


@router.get("/me")
async def get_current_user(
    current_user: SupabaseUserInfo = Depends(get_current_user_from_jwt),
    api_key_auth: APIKeyAuth = Depends(get_api_key_auth),
):
    """
    Get current user information.

    Args:
        current_user: Current user from JWT token
        api_key_auth: API key authentication service

    Returns:
        User information
    """
    try:
        # Get user from MongoDB
        user = await api_key_auth.create_or_get_user(current_user.sub, current_user.email)

        return {
            "id": user.id,
            "supabase_id": user.supabase_id,
            "email": user.email,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "api_key_count": len(user.api_keys),
        }

    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information",
        )
