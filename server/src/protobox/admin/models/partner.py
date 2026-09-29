"""Partner models for B2B2C integration."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Partner(BaseModel):
    """Partner organization model."""

    id: str
    name: str
    partner_id: str
    secret_key: str
    allowed_endpoints: list[str]
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class PartnerAuthRequest(BaseModel):
    """Partner authentication request model."""

    partner_id: str
    partner_user_id: str
    timestamp: int
    data: dict[str, Any] | None = None


class TenantCreate(BaseModel):
    """Tenant creation request model."""

    tenant_id: str
    name: str | None = None
    settings: dict[str, Any] | None = None


class TenantResponse(BaseModel):
    """Tenant response model."""

    workspace_id: str
    tenant_id: str
    status: str

    def dict(self, **kwargs):
        """Compatibility method for older Pydantic versions."""
        return self.model_dump(**kwargs)
