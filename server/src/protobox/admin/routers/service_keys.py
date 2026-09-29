"""Service API keys router for administrative management."""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..auth.service_key_auth import ServiceKeyAuth, get_service_key_auth

router = APIRouter(prefix="/service-keys", tags=["service-keys"])


class CreateServiceKeyRequest(BaseModel):
    """Request to create a service API key."""

    service_name: str = Field(..., description="Service name (e.g., 'mcp-server')")
    scopes: list[str] = Field(..., description="Permission scopes")
    description: str | None = Field(None, description="Optional description")


class CreateServiceKeyResponse(BaseModel):
    """Response with service key details."""

    key_id: str = Field(..., description="Service key ID")
    service_name: str = Field(..., description="Service name")
    secret_key: str = Field(..., description="Secret key (only shown once)")
    scopes: list[str] = Field(..., description="Permission scopes")
    description: str | None = Field(None, description="Description")


class ServiceKeyInfo(BaseModel):
    """Service key information (without secret)."""

    key_id: str = Field(..., description="Service key ID")
    service_name: str = Field(..., description="Service name")
    scopes: list[str] = Field(..., description="Permission scopes")
    description: str | None = Field(None, description="Description")
    is_active: bool = Field(..., description="Whether key is active")
    last_used_at: str | None = Field(None, description="Last usage timestamp")
    created_at: str = Field(..., description="Creation timestamp")


@router.post("", response_model=CreateServiceKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_service_key(
    request: CreateServiceKeyRequest,
    current_user: User = Depends(require_authentication),
    service_key_auth: ServiceKeyAuth = Depends(get_service_key_auth),
):
    """
    Create a new service API key.

    Only authenticated users can create service keys.
    """
    try:
        service_key, secret_key = await service_key_auth.create_service_key(
            service_name=request.service_name,
            scopes=request.scopes,
            created_by=current_user.id,
            description=request.description,
        )

        logger.info(
            f"Service key created: {service_key.service_name} by {current_user.email}"
        )

        return CreateServiceKeyResponse(
            key_id=service_key.id,
            service_name=service_key.service_name,
            secret_key=secret_key,
            scopes=service_key.scopes,
            description=service_key.description,
        )

    except Exception as e:
        logger.error(f"Failed to create service key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create service key: {str(e)}",
        )


@router.get("", response_model=list[ServiceKeyInfo])
async def list_service_keys(
    current_user: User = Depends(require_authentication),
    service_key_auth: ServiceKeyAuth = Depends(get_service_key_auth),
):
    """
    List all service API keys.

    Only authenticated users can list service keys.
    """
    try:
        keys = await service_key_auth.list_service_keys()

        return [
            ServiceKeyInfo(
                key_id=key.id,
                service_name=key.service_name,
                scopes=key.scopes,
                description=key.description,
                is_active=key.is_active,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                created_at=key.created_at.isoformat(),
            )
            for key in keys
        ]

    except Exception as e:
        logger.error(f"Failed to list service keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list service keys: {str(e)}",
        )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_service_key(
    key_id: str,
    current_user: User = Depends(require_authentication),
    service_key_auth: ServiceKeyAuth = Depends(get_service_key_auth),
):
    """
    Revoke a service API key.

    Only authenticated users can revoke service keys.
    """
    try:
        # Validate key_id format
        ObjectId(key_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid service key ID format",
        )

    try:
        success = await service_key_auth.revoke_service_key(key_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service key not found",
            )

        logger.info(f"Service key revoked: {key_id} by {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke service key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke service key: {str(e)}",
        )
