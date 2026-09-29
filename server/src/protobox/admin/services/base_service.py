"""Base service class with common audit functionality."""

from abc import ABC
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager

from fastapi import Depends
from ..constants import SystemUsers
from ..auth.dependencies import get_current_user_jwt
from ..auth.models import User


class AuditMixin:
    """Mixin class providing audit field management."""
    
    @staticmethod
    def add_create_audit_fields(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Add creation audit fields to data."""
        now = datetime.utcnow()
        return {
            **data,
            "created_by": user_id,
            "updated_by": user_id,
            "created_at": now,
            "updated_at": now
        }
    
    @staticmethod
    def ensure_audit_fields(data: Dict[str, Any], default_user_id: str = "system") -> Dict[str, Any]:
        """Ensure audit fields are present, using defaults for missing values."""
        now = datetime.utcnow()
        return {
            **data,
            "created_by": data.get("created_by") or default_user_id,
            "updated_by": data.get("updated_by") or default_user_id,
            "created_at": data.get("created_at") or now,
            "updated_at": data.get("updated_at") or now
        }
    
    @staticmethod 
    def add_update_audit_fields(updates: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Add update audit fields to updates."""
        return {
            **updates,
            "updated_by": user_id,
            "updated_at": datetime.utcnow()
        }
    
    @staticmethod
    def get_system_user_id(system_type: str = SystemUsers.SYSTEM) -> str:
        """Get system user ID for system operations."""
        return system_type


class BaseService(AuditMixin, ABC):
    """Base service class with common functionality."""
    
    def __init__(self, repository=None):
        """Initialize base service."""
        self.repository = repository
    
    async def create_with_audit(self, model_class, data: Dict[str, Any], user_id: str):
        """Create a model with audit fields."""
        audit_data = self.add_create_audit_fields(data, user_id)
        model = model_class(**audit_data)
        return await self.repository.create(model)
    
    async def update_with_audit(self, record_id: str, updates: Dict[str, Any], user_id: str):
        """Update a record with audit fields."""
        audit_updates = self.add_update_audit_fields(updates, user_id)
        return await self.repository.update(record_id, audit_updates)