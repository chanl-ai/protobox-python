"""
Workspace management router for handling workspace CRUD operations.

Provides endpoints for:
- Workspace creation and management
- Workspace member management
- Workspace settings and billing
"""

import os
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..auth.dependencies import require_authentication
from ..auth.models import User as AuthUser
from ..middleware.team_auth import require_workspace_access, require_workspace_management_permission
from ..models.team_member import WorkspaceMember
from ..database.connection import get_database_connection
from ..utils.slug_validator import (
    sanitize_slug,
    suggest_alternative_slug,
    validate_slug,
)


def get_db():
    """Get database connection."""
    db_conn = get_database_connection()
    return db_conn.database


router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


class WorkspaceMember(BaseModel):
    """Workspace member model."""

    user_id: str
    role: str = Field(pattern="^(owner|admin|member|viewer)$")
    joined_at: datetime
    invited_by: str | None = None


class WorkspaceSettings(BaseModel):
    """Workspace settings model."""

    default_model: str = Field(default="gpt-4o-mini")
    max_file_size: int = Field(default=10485760)  # 10MB
    allowed_file_types: list[str] = Field(default_factory=lambda: [".txt", ".pdf", ".md"])
    enable_code_execution: bool = Field(default=False)
    enable_web_search: bool = Field(default=True)


class WorkspaceBilling(BaseModel):
    """Workspace billing model."""

    plan: str = Field(default="free", pattern="^(free|starter|pro|enterprise)$")
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


class Workspace(BaseModel):
    """Workspace model."""

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: str = Field(alias="_id")
    name: str
    description: str | None = None
    slug: str | None = None
    owner_id: str
    members: list[WorkspaceMember]
    settings: WorkspaceSettings | None = None
    billing: WorkspaceBilling | None = None
    created_at: datetime
    updated_at: datetime


class CreateWorkspaceRequest(BaseModel):
    """Request model for creating a workspace."""

    name: str
    description: str | None = None


class UpdateWorkspaceRequest(BaseModel):
    """Request model for updating a workspace."""

    name: str | None = None
    description: str | None = None
    slug: str | None = None
    settings: WorkspaceSettings | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v):
        """Validate the slug format."""
        if v is not None:
            is_valid, error = validate_slug(v)
            if not is_valid:
                raise ValueError(error)
        return v


class AddMemberRequest(BaseModel):
    """Request model for adding a workspace member."""

    user_email: str
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


@router.get("/", response_model=list[Workspace])
async def list_workspaces(
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """List all workspaces the current user has access to."""
    from ..middleware.team_auth import get_team_auth_service

    # Use team-based authentication to get user's workspaces
    team_auth = await get_team_auth_service()
    user_memberships = await team_auth.get_user_workspaces(current_user.id)

    if not user_memberships:
        return []

    # Get workspace details for each membership
    workspaces_collection = db.workspaces
    workspace_ids = [membership.workspace_id for membership in user_memberships]

    workspaces = await workspaces_collection.find(
        {"_id": {"$in": workspace_ids}}
    ).to_list(None)

    # Convert ObjectIds to strings and ensure required fields
    for workspace in workspaces:
        workspace["_id"] = str(workspace["_id"])

        # Add default values for optional fields if not present
        if "settings" not in workspace:
            workspace["settings"] = None
        if "billing" not in workspace:
            workspace["billing"] = None

    return [Workspace(**w) for w in workspaces]


@router.post("/", response_model=Workspace)
async def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Create a new workspace."""
    workspaces_collection = db.workspaces
    users_collection = db.users

    # Generate slug from name if not provided
    import re

    slug = re.sub(r"[^a-z0-9-]", "-", request.name.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)  # Replace multiple hyphens with single

    # Create workspace document
    workspace_doc = {
        "_id": ObjectId(),
        "name": request.name,
        "description": request.description,
        "slug": slug,
        "owner_id": current_user.id,
        "members": [
            {
                "user_id": current_user.id,
                "role": "owner",
                "joined_at": datetime.utcnow(),
                "invited_by": None,
            }
        ],
        "settings": {
            "default_model": "gpt-4o-mini",
            "max_file_size": 10485760,
            "allowed_file_types": [".txt", ".pdf", ".md"],
            "enable_code_execution": False,
            "enable_web_search": True,
        },
        "billing": {
            "plan": "free",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "current_period_start": None,
            "current_period_end": None,
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # Insert workspace
    await workspaces_collection.insert_one(workspace_doc)

    # Add creator to workspace_members collection (team-based auth)
    from ..middleware.team_auth import get_team_auth_service
    from ..models.team_member import WorkspaceMember, MemberRole

    team_auth = await get_team_auth_service()

    # Get user details for workspace member creation
    user = await users_collection.find_one({"firebase_uid": current_user.id})
    user_email = user.get("email") if user else None

    # Create workspace member record
    workspace_member = WorkspaceMember(
        workspace_id=workspace_doc["_id"],
        user_id=current_user.id,
        email=user_email,
        display_name=(user or {}).get("displayName") or (user_email.split("@")[0] if user_email else current_user.id),
        role=MemberRole.OWNER,
        invited_by=None,  # Self-created
        joined_at=datetime.utcnow(),
    )

    # Save to workspace_members collection
    await team_auth.team_member_repo.create_member(workspace_member)

    # Add workspace to user's workspace list
    await users_collection.update_one(
        {"firebase_uid": current_user.id},
        {"$push": {"workspaces": workspace_doc["_id"]}, "$set": {"updated_at": datetime.utcnow()}},
    )

    # Convert ObjectId to string for response
    workspace_doc["_id"] = str(workspace_doc["_id"])

    return Workspace(**workspace_doc)


@router.get("/{workspace_id}", response_model=Workspace)
async def get_workspace(
    workspace_id: str,
    member: WorkspaceMember = Depends(require_workspace_access),
    db=Depends(get_db),
):
    """Get a workspace by ID."""
    workspaces_collection = db.workspaces

    try:
        workspace = await workspaces_collection.find_one({"_id": ObjectId(workspace_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace["_id"] = str(workspace["_id"])
    # Add default values for optional fields if not present
    if "settings" not in workspace:
        workspace["settings"] = None
    if "billing" not in workspace:
        workspace["billing"] = None
    if "slug" not in workspace or workspace["slug"] is None:
        # Generate slug from name
        import re

        workspace["slug"] = re.sub(r"[^a-z0-9-]", "-", workspace["name"].lower()).strip("-")
        workspace["slug"] = re.sub(r"-+", "-", workspace["slug"])

    return Workspace(**workspace)


@router.patch("/{workspace_id}", response_model=Workspace)
async def update_workspace(
    workspace_id: str,
    request: UpdateWorkspaceRequest,
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Update a workspace (requires admin or owner role)."""
    from ..middleware.team_auth import get_team_auth_service
    from ..models.team_member import MemberRole

    # Check if user has admin/owner access using team-based auth
    team_auth = await get_team_auth_service()

    try:
        # Verify user has admin or owner role
        member = await team_auth.verify_workspace_access(
            ObjectId(workspace_id), current_user.id, min_role=MemberRole.ADMIN
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    workspaces_collection = db.workspaces

    # Build update document
    update_doc = {}
    if request.name is not None:
        update_doc["name"] = request.name
    if request.description is not None:
        update_doc["description"] = request.description
    if request.slug is not None:
        # Check if slug is already taken by another workspace
        existing = await workspaces_collection.find_one(
            {"slug": request.slug, "_id": {"$ne": ObjectId(workspace_id)}}
        )
        if existing:
            raise HTTPException(status_code=400, detail=f"Slug '{request.slug}' is already taken")
        update_doc["slug"] = request.slug
    if request.settings is not None:
        update_doc["settings"] = request.settings.model_dump()

    if not update_doc:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_doc["updated_at"] = datetime.utcnow()

    # Update workspace
    await workspaces_collection.update_one({"_id": ObjectId(workspace_id)}, {"$set": update_doc})

    # Get updated workspace
    workspace = await workspaces_collection.find_one({"_id": ObjectId(workspace_id)})
    workspace["_id"] = str(workspace["_id"])
    # Add default values for optional fields if not present
    if "settings" not in workspace:
        workspace["settings"] = None
    if "billing" not in workspace:
        workspace["billing"] = None
    if "slug" not in workspace or workspace["slug"] is None:
        # Generate slug from name
        import re

        workspace["slug"] = re.sub(r"[^a-z0-9-]", "-", workspace["name"].lower()).strip("-")
        workspace["slug"] = re.sub(r"-+", "-", workspace["slug"])

    return Workspace(**workspace)


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str, current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Delete a workspace (requires owner role)."""
    workspaces_collection = db.workspaces
    users_collection = db.users

    # Check if user is owner
    try:
        workspace = await workspaces_collection.find_one(
            {"_id": ObjectId(workspace_id), "owner_id": current_user.id}
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied - owner role required")

    # Remove workspace from all users
    await users_collection.update_many(
        {"workspaces": ObjectId(workspace_id)}, {"$pull": {"workspaces": ObjectId(workspace_id)}}
    )

    # Delete workspace
    await workspaces_collection.delete_one({"_id": ObjectId(workspace_id)})

    return {"message": "Workspace deleted successfully"}


@router.get("/{workspace_id}/members", response_model=list[dict[str, Any]])
async def list_workspace_members(
    workspace_id: str,
    member: WorkspaceMember = Depends(require_workspace_access),
    db=Depends(get_db),
):
    """List all members of a workspace."""
    from ..middleware.team_auth import get_team_auth_service

    # Use team-based authentication to get workspace members
    team_auth = await get_team_auth_service()

    try:
        # Get all members from the workspace_members collection
        workspace_members = await team_auth.team_member_repo.get_members_by_workspace(
            ObjectId(workspace_id)
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    # Get user details for each member
    users_collection = db.users
    members_with_details = []

    for workspace_member in workspace_members:
        user = await users_collection.find_one(
            {"firebase_uid": workspace_member.user_id}, {"email": 1, "displayName": 1}
        )

        if user:
            members_with_details.append(
                {
                    "user_id": workspace_member.user_id,
                    "email": user.get("email"),
                    "display_name": user.get("displayName"),
                    "role": workspace_member.role.value,
                    "joined_at": workspace_member.joined_at,
                    "invited_by": workspace_member.invited_by,
                }
            )

    return members_with_details


@router.post("/{workspace_id}/members", response_model=dict[str, str])
async def add_workspace_member(
    workspace_id: str,
    request: AddMemberRequest,
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Add a member to a workspace (requires admin or owner role)."""
    workspaces_collection = db.workspaces
    users_collection = db.users

    # Check if user has admin/owner access
    try:
        workspace = await workspaces_collection.find_one(
            {
                "_id": ObjectId(workspace_id),
                "members": {
                    "$elemMatch": {"user_id": current_user.id, "role": {"$in": ["owner", "admin"]}}
                },
            }
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied - admin or owner role required")

    # Find user by email
    user = await users_collection.find_one({"email": request.user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is already a member
    if any(m["user_id"] == user["firebase_uid"] for m in workspace["members"]):
        raise HTTPException(status_code=400, detail="User is already a member")

    # Add member
    new_member = {
        "user_id": user["firebase_uid"],
        "role": request.role,
        "joined_at": datetime.utcnow(),
        "invited_by": current_user.id,
    }

    await workspaces_collection.update_one(
        {"_id": ObjectId(workspace_id)},
        {"$push": {"members": new_member}, "$set": {"updated_at": datetime.utcnow()}},
    )

    # Add workspace to user's list
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$push": {"workspaces": ObjectId(workspace_id)},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )

    return {"message": "Member added successfully"}


@router.delete("/{workspace_id}/members/{user_id}")
async def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Remove a member from a workspace."""
    workspaces_collection = db.workspaces
    users_collection = db.users

    # Get workspace
    try:
        workspace = await workspaces_collection.find_one({"_id": ObjectId(workspace_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check permissions
    current_member = next(
        (m for m in workspace["members"] if m["user_id"] == current_user.id), None
    )

    if not current_member:
        raise HTTPException(status_code=403, detail="Access denied")

    # Users can remove themselves, admins/owners can remove others
    if user_id != current_user.id and current_member["role"] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied - can only remove yourself")

    # Can't remove the owner
    if user_id == workspace["owner_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove workspace owner")

    # Remove member
    await workspaces_collection.update_one(
        {"_id": ObjectId(workspace_id)},
        {"$pull": {"members": {"user_id": user_id}}, "$set": {"updated_at": datetime.utcnow()}},
    )

    # Remove workspace from user's list
    user = await users_collection.find_one({"firebase_uid": user_id})
    if user:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$pull": {"workspaces": ObjectId(workspace_id)},
                "$set": {"updated_at": datetime.utcnow()},
            },
        )

    return {"message": "Member removed successfully"}


# ==================== Workspace Settings Endpoints ====================


@router.get("/{workspace_id}/settings", response_model=WorkspaceSettings)
async def get_workspace_settings(
    workspace_id: str,
    member: WorkspaceMember = Depends(require_workspace_access),
    db=Depends(get_db),
):
    """Get workspace settings."""
    workspaces_collection = db.workspaces

    # Get workspace (access already validated by require_workspace_access)
    try:
        workspace = await workspaces_collection.find_one({"_id": ObjectId(workspace_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Return settings or default if not set
    settings = workspace.get("settings")
    if not settings:
        # Return default settings
        settings = {
            "notifications_enabled": True,
            "auto_export_enabled": False,
            "default_timezone": "UTC",
            "date_format": "YYYY-MM-DD",
            "time_format": "24h",
            "language": "en",
            "theme": "light",
        }

    return WorkspaceSettings(**settings)


@router.put("/{workspace_id}/settings", response_model=WorkspaceSettings)
async def update_workspace_settings(
    workspace_id: str,
    settings: WorkspaceSettings,
    member: WorkspaceMember = Depends(require_workspace_management_permission),
    db=Depends(get_db),
):
    """Update workspace settings (requires workspace management permission)."""
    workspaces_collection = db.workspaces

    # Get workspace (access already validated by require_workspace_management_permission)
    try:
        workspace = await workspaces_collection.find_one({"_id": ObjectId(workspace_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid workspace ID")

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Update settings
    await workspaces_collection.update_one(
        {"_id": ObjectId(workspace_id)},
        {"$set": {"settings": settings.model_dump(), "updated_at": datetime.utcnow()}},
    )

    logger.info(f"Workspace {workspace_id} settings updated by user {current_user.id}")

    return settings


# ==================== Slug Management Endpoints ====================


@router.post("/{workspace_id}/check-slug")
async def check_slug_availability(
    workspace_id: str,
    slug: str = Query(..., description="The slug to check"),
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Check if a slug is available for use."""
    workspaces_collection = db.workspaces

    # Validate the slug format
    is_valid, error = validate_slug(slug)
    if not is_valid:
        return {"available": False, "valid": False, "error": error, "suggested_alternatives": []}

    # Check if slug is already taken by another workspace
    existing = await workspaces_collection.find_one(
        {"slug": slug, "_id": {"$ne": ObjectId(workspace_id)}}
    )

    if existing:
        # Get all existing slugs for suggesting alternatives
        all_slugs = await workspaces_collection.distinct("slug")
        alternatives = []

        # Try to suggest alternatives
        base_slug = slug.rstrip("0123456789-")  # Remove trailing numbers and hyphens
        for i in range(1, 6):
            suggested = f"{base_slug}-{i}"
            if suggested not in all_slugs:
                alternatives.append(suggested)
                if len(alternatives) >= 3:
                    break

        return {
            "available": False,
            "valid": True,
            "error": f"The slug '{slug}' is already taken",
            "suggested_alternatives": alternatives,
        }

    return {"available": True, "valid": True, "error": None, "suggested_alternatives": []}


@router.post("/{workspace_id}/suggest-slug")
async def suggest_slug(
    workspace_id: str,
    name: str = Query(..., description="The name to generate a slug from"),
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Suggest a slug based on a workspace name."""
    workspaces_collection = db.workspaces

    # Sanitize the name to create a base slug
    base_slug = sanitize_slug(name)

    # Get all existing slugs
    all_slugs = await workspaces_collection.distinct("slug")

    # Find an available variation
    suggested = suggest_alternative_slug(base_slug, all_slugs)

    if not suggested:
        # Fallback: use workspace ID suffix
        suggested = f"{base_slug}-{workspace_id[-6:]}"

    return {
        "suggested_slug": suggested,
        "base_slug": base_slug,
        "preview_url": f"https://{suggested}.{os.getenv('WORKSPACE_DOMAIN', 'example.com')}",
    }


# ==================== Workspace Stats Endpoints ====================


class WorkspaceStats(BaseModel):
    """Workspace statistics model."""
    
    actions_count: int = 0
    mcp_tokens_count: int = 0
    oauth_clients_count: int = 0
    integrations_count: int = 0
    knowledge_docs_count: int = 0
    

@router.get("/{workspace_id}/stats", response_model=WorkspaceStats)
async def get_workspace_stats(
    workspace_id: str,
    member: WorkspaceMember = Depends(require_workspace_access),
    db=Depends(get_db),
):
    """Get workspace statistics and counts."""
    # Authentication handled by require_workspace_access dependency
    # member object contains verified workspace membership
    
    # Count documents in parallel
    stats = {}
    
    # Actions count
    stats["actions_count"] = await db.actions.count_documents({"workspace_id": workspace_id})
    
    # MCP tokens count
    stats["mcp_tokens_count"] = await db.mcp_tokens.count_documents({
        "workspace_id": workspace_id,
        "status": {"$ne": "deleted"}
    })
    
    # OAuth clients count  
    stats["oauth_clients_count"] = await db.oauth_clients.count_documents({
        "workspace_id": workspace_id,
        "deleted_at": {"$exists": False}
    })
    
    # Integrations count
    stats["integrations_count"] = await db.integrations.count_documents({
        "workspace_id": workspace_id,
        "status": {"$ne": "deleted"}
    })
    
    # Knowledge base documents count
    stats["knowledge_docs_count"] = await db.knowledge_documents.count_documents({
        "workspace_id": workspace_id,
        "status": {"$ne": "deleted"}
    })
    
    return WorkspaceStats(**stats)
