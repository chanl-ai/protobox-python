"""Action template model for database storage."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TemplateCategory(str, Enum):
    """Template category enumeration."""
    
    CALENDAR_SCHEDULING = "calendar_scheduling"
    COMMUNICATION = "communication"
    FILE_MANAGEMENT = "file_management"
    PROJECT_MANAGEMENT = "project_management"
    DATA_ANALYTICS = "data_analytics"
    AUTOMATION = "automation"
    SECURITY = "security"
    MONITORING = "monitoring"
    STORAGE = "storage"  # For Google Drive
    PRODUCTIVITY = "productivity"  # For Google Sheets, Docs
    CUSTOM = "custom"


class TemplateStatus(str, Enum):
    """Template status enumeration."""
    
    ACTIVE = "active"
    BETA = "beta"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    DRAFT = "draft"


class ActionTemplateModel(BaseModel):
    """Action template model for MongoDB storage."""

    id: str | None = Field(None, alias="_id")
    template_id: str  # Unique identifier like "gmail_send_email"
    name: str
    description: str
    category: str  # calendar_scheduling, communication, file_management, etc.
    capability: str  # IntegrationCapability value
    
    # Integration requirements
    required_integrations: list[str] = Field(default_factory=list)
    optional_integrations: list[str] = Field(default_factory=list)
    
    # Configuration
    config_schema: dict[str, Any] = Field(default_factory=dict)
    default_config: dict[str, Any] = Field(default_factory=dict)
    integration_config: dict[str, dict[str, Any]] = Field(default_factory=dict)
    
    # Metadata
    tags: list[str] = Field(default_factory=list)
    is_active: bool = True
    status: str = "active"  # Using TemplateStatus values
    version: str = "1.0.0"
    popularity_score: float = 0.0  # Added for template ranking
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )
    
    def model_dump_for_db(self) -> dict:
        """Convert model to dict for database storage."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        data["updated_at"] = datetime.now(UTC)
        return data
    
    def is_available(self, connected_integrations: list[str]) -> bool:
        """Check if this template can be used with current integrations."""
        return all(req in connected_integrations for req in self.required_integrations)