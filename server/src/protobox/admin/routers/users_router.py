"""
User management router for handling user profiles and preferences.

Provides endpoints for:
- User profile management
- User preferences
- User workspace associations
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..auth.dependencies import require_authentication
from ..auth.models import User as AuthUser
from ..database.connection import get_database_connection


def get_db():
    """Get database connection."""
    db_conn = get_database_connection()
    return db_conn.database


router = APIRouter(prefix="/users", tags=["Users"])


def _convert_objectids_to_strings(data: dict) -> dict:
    """Convert MongoDB ObjectIds to strings in a dictionary."""
    if not data:
        return data
    
    result = data.copy()
    for key, value in result.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, dict):
            result[key] = _convert_objectids_to_strings(value)
    return result


class UserPreferences(BaseModel):
    """User preferences model."""

    theme: str = Field(default="light", pattern="^(light|dark)$")
    language: str = Field(default="en")
    timezone: str = Field(default="UTC")
    email_notifications: bool = Field(default=True)
    last_workspace_id: str | None = None


class User(BaseModel):
    """User model."""

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    id: str = Field(alias="_id")
    email: str
    display_name: str = Field(alias="displayName")
    firebase_uid: str
    preferences: UserPreferences
    workspaces: list[str]
    created_at: datetime
    updated_at: datetime


class CreateUserRequest(BaseModel):
    """Request model for creating a user."""

    email: str
    display_name: str = Field(alias="displayName")
    firebase_uid: str


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    display_name: str | None = Field(None, alias="displayName")
    email: str | None = None


class UpdatePreferencesRequest(BaseModel):
    """Request model for updating user preferences."""

    theme: str | None = Field(None, pattern="^(light|dark)$")
    language: str | None = None
    timezone: str | None = None
    email_notifications: bool | None = Field(None, alias="emailNotifications")
    last_workspace_id: str | None = Field(None, alias="lastWorkspaceId")


@router.get("/me", response_model=User)
async def get_current_user_profile(
    current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Get the current user's profile."""
    users_collection = db.users

    # Find user by Firebase UID (user should already exist from token exchange)
    user = await users_collection.find_one({"firebase_uid": current_user.id})

    if not user:
        # This should not happen if token exchange is working properly
        # But we'll handle it gracefully for backward compatibility
        raise HTTPException(
            status_code=404, detail="User profile not found. Please re-authenticate."
        )

    # Convert ObjectId to string for response
    user["_id"] = str(user["_id"])
    user["workspaces"] = [str(w) for w in user.get("workspaces", [])]

    return User(**user)


@router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences(
    current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Get the current user's preferences."""
    users_collection = db.users

    user = await users_collection.find_one({"firebase_uid": current_user.id}, {"preferences": 1})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    preferences = _convert_objectids_to_strings(user.get("preferences", {}))
    return UserPreferences(**preferences)


@router.patch("/preferences", response_model=UserPreferences)
async def update_user_preferences(
    request: UpdatePreferencesRequest,
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Update the current user's preferences."""
    users_collection = db.users

    # Build update document
    update_doc = {}
    if request.theme is not None:
        update_doc["preferences.theme"] = request.theme
    if request.language is not None:
        update_doc["preferences.language"] = request.language
    if request.timezone is not None:
        update_doc["preferences.timezone"] = request.timezone
    if request.email_notifications is not None:
        update_doc["preferences.email_notifications"] = request.email_notifications
    if request.last_workspace_id is not None:
        update_doc["preferences.last_workspace_id"] = request.last_workspace_id

    if not update_doc:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_doc["updated_at"] = datetime.utcnow()

    # Update user
    result = await users_collection.update_one(
        {"firebase_uid": current_user.id}, {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    # Get updated preferences
    user = await users_collection.find_one({"firebase_uid": current_user.id}, {"preferences": 1})

    preferences = _convert_objectids_to_strings(user.get("preferences", {}))
    return UserPreferences(**preferences)


@router.patch("/last-workspace", response_model=dict[str, str])
async def update_last_workspace(
    workspace_id: str, current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Update the user's last workspace."""
    users_collection = db.users

    # Verify workspace exists and user has access
    workspaces_collection = db.workspaces
    workspace = await workspaces_collection.find_one(
        {"_id": ObjectId(workspace_id), "members.user_id": current_user.id}
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    # Update user's last workspace
    result = await users_collection.update_one(
        {"firebase_uid": current_user.id},
        {"$set": {"preferences.last_workspace_id": workspace_id, "updated_at": datetime.utcnow()}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"workspace_id": workspace_id}


@router.get("/{user_id}", response_model=User)
async def get_user_by_id(
    user_id: str, current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Get a user by ID (requires workspace membership check)."""
    users_collection = db.users

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if current user shares a workspace with target user
    workspaces_collection = db.workspaces
    shared_workspace = await workspaces_collection.find_one(
        {"$and": [{"members.user_id": current_user.id}, {"members.user_id": user["firebase_uid"]}]}
    )

    if not shared_workspace and current_user.id != user["firebase_uid"]:
        raise HTTPException(status_code=403, detail="Access denied - no shared workspace")

    # Convert ObjectId to string for response
    user["_id"] = str(user["_id"])
    user["workspaces"] = [str(w) for w in user.get("workspaces", [])]

    return User(**user)
