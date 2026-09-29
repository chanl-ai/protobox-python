"""
Billing management router for handling subscriptions and usage tracking.

Provides endpoints for:
- Subscription management
- Usage tracking and metrics
- Billing information
- Plan limits and quotas
"""

from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth.dependencies import require_authentication
from ..auth.models import User as AuthUser
from ..database.connection import get_database_connection


def get_db():
    """Get database connection."""
    db_conn = get_database_connection()
    return db_conn.database


router = APIRouter(prefix="/billing", tags=["Billing"])


class PlanLimits(BaseModel):
    """Plan limits model."""

    max_messages_per_month: int
    max_file_uploads_per_month: int
    max_file_size_mb: int
    max_workspaces: int
    max_members_per_workspace: int
    advanced_models: bool
    priority_support: bool


class UsageData(BaseModel):
    """Usage data model."""

    messages_sent: int = Field(default=0)
    files_uploaded: int = Field(default=0)
    tokens_used: int = Field(default=0)
    api_calls: int = Field(default=0)


class UsageMetrics(BaseModel):
    """Usage metrics model."""

    workspace_id: str
    period_start: datetime
    period_end: datetime
    usage: UsageData
    limits: PlanLimits
    updated_at: datetime


class Subscription(BaseModel):
    """Subscription model."""

    workspace_id: str
    plan: str = Field(pattern="^(free|starter|pro|enterprise)$")
    status: str = Field(pattern="^(active|canceled|past_due|trialing)$")
    stripe_subscription_id: str | None = None
    stripe_customer_id: str | None = None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime


class BillingInfo(BaseModel):
    """Billing information model."""

    workspace_id: str
    subscription: Subscription
    usage: UsageMetrics
    payment_method: dict[str, Any] | None = None
    invoices: list[dict[str, Any]] = Field(default_factory=list)


# Plan limits configuration
PLAN_LIMITS = {
    "free": PlanLimits(
        max_messages_per_month=100,
        max_file_uploads_per_month=10,
        max_file_size_mb=5,
        max_workspaces=1,
        max_members_per_workspace=3,
        advanced_models=False,
        priority_support=False,
    ),
    "starter": PlanLimits(
        max_messages_per_month=1000,
        max_file_uploads_per_month=100,
        max_file_size_mb=10,
        max_workspaces=3,
        max_members_per_workspace=10,
        advanced_models=True,
        priority_support=False,
    ),
    "pro": PlanLimits(
        max_messages_per_month=10000,
        max_file_uploads_per_month=1000,
        max_file_size_mb=50,
        max_workspaces=10,
        max_members_per_workspace=50,
        advanced_models=True,
        priority_support=True,
    ),
    "enterprise": PlanLimits(
        max_messages_per_month=999999,
        max_file_uploads_per_month=999999,
        max_file_size_mb=100,
        max_workspaces=999,
        max_members_per_workspace=999,
        advanced_models=True,
        priority_support=True,
    ),
}


async def get_workspace_subscription(workspace_id: str, db) -> Subscription:
    """Get or create subscription for workspace."""
    subscriptions_collection = db.subscriptions

    subscription = await subscriptions_collection.find_one({"workspace_id": workspace_id})

    if not subscription:
        # Create default free subscription
        subscription = {
            "workspace_id": workspace_id,
            "plan": "free",
            "status": "active",
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
            "cancel_at_period_end": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await subscriptions_collection.insert_one(subscription)

    return Subscription(**subscription)


async def get_workspace_usage(workspace_id: str, db) -> UsageMetrics:
    """Get or create usage metrics for workspace."""
    usage_collection = db.usage_metrics

    # Get current period
    subscription = await get_workspace_subscription(workspace_id, db)

    usage = await usage_collection.find_one(
        {"workspace_id": workspace_id, "period_start": subscription.current_period_start}
    )

    if not usage:
        # Create usage metrics for current period
        usage = {
            "workspace_id": workspace_id,
            "period_start": subscription.current_period_start,
            "period_end": subscription.current_period_end,
            "usage": {"messages_sent": 0, "files_uploaded": 0, "tokens_used": 0, "api_calls": 0},
            "limits": PLAN_LIMITS[subscription.plan].model_dump(),
            "updated_at": datetime.utcnow(),
        }
        await usage_collection.insert_one(usage)

    return UsageMetrics(**usage)


@router.get("/{workspace_id}", response_model=BillingInfo)
async def get_billing_info(
    workspace_id: str, current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Get billing information for a workspace."""
    # Verify user has access to workspace
    workspaces_collection = db.workspaces
    workspace = await workspaces_collection.find_one(
        {"_id": ObjectId(workspace_id), "members.user_id": current_user.id}
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    # Get subscription and usage
    subscription = await get_workspace_subscription(workspace_id, db)
    usage = await get_workspace_usage(workspace_id, db)

    return BillingInfo(
        workspace_id=workspace_id,
        subscription=subscription,
        usage=usage,
        payment_method=None,
        invoices=[],
    )


@router.get("/{workspace_id}/usage", response_model=UsageMetrics)
async def get_usage_metrics(
    workspace_id: str, current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Get usage metrics for a workspace."""
    # Verify user has access to workspace
    workspaces_collection = db.workspaces
    workspace = await workspaces_collection.find_one(
        {"_id": ObjectId(workspace_id), "members.user_id": current_user.id}
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    return await get_workspace_usage(workspace_id, db)


@router.post("/{workspace_id}/usage/track")
async def track_usage(
    workspace_id: str,
    usage_type: str = Query(..., pattern="^(message|file|token|api)$"),
    amount: int = Query(1, ge=1),
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Track usage for a workspace."""
    # Verify user has access to workspace
    workspaces_collection = db.workspaces
    workspace = await workspaces_collection.find_one(
        {"_id": ObjectId(workspace_id), "members.user_id": current_user.id}
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    # Get current usage
    usage_collection = db.usage_metrics
    subscription = await get_workspace_subscription(workspace_id, db)

    # Update usage based on type
    update_field = {
        "message": "usage.messages_sent",
        "file": "usage.files_uploaded",
        "token": "usage.tokens_used",
        "api": "usage.api_calls",
    }[usage_type]

    await usage_collection.update_one(
        {"workspace_id": workspace_id, "period_start": subscription.current_period_start},
        {"$inc": {update_field: amount}, "$set": {"updated_at": datetime.utcnow()}},
        upsert=True,
    )

    # Check if limits exceeded
    usage = await get_workspace_usage(workspace_id, db)
    limits = PLAN_LIMITS[subscription.plan]

    if usage_type == "message" and usage.usage.messages_sent > limits.max_messages_per_month:
        return {
            "tracked": True,
            "limit_exceeded": True,
            "message": "Monthly message limit exceeded",
        }
    if usage_type == "file" and usage.usage.files_uploaded > limits.max_file_uploads_per_month:
        return {
            "tracked": True,
            "limit_exceeded": True,
            "message": "Monthly file upload limit exceeded",
        }

    return {"tracked": True, "limit_exceeded": False, "current_usage": usage.usage.model_dump()}


@router.get("/{workspace_id}/limits", response_model=PlanLimits)
async def get_plan_limits(
    workspace_id: str, current_user: AuthUser = Depends(require_authentication), db=Depends(get_db)
):
    """Get plan limits for a workspace."""
    # Verify user has access to workspace
    workspaces_collection = db.workspaces
    workspace = await workspaces_collection.find_one(
        {"_id": ObjectId(workspace_id), "members.user_id": current_user.id}
    )

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")

    subscription = await get_workspace_subscription(workspace_id, db)
    return PLAN_LIMITS[subscription.plan]


@router.post("/{workspace_id}/subscription/upgrade")
async def upgrade_subscription(
    workspace_id: str,
    new_plan: str = Query(..., pattern="^(starter|pro|enterprise)$"),
    current_user: AuthUser = Depends(require_authentication),
    db=Depends(get_db),
):
    """Upgrade workspace subscription (requires owner role)."""
    # Verify user is workspace owner
    workspaces_collection = db.workspaces
    workspace = await workspaces_collection.find_one(
        {"_id": ObjectId(workspace_id), "owner_id": current_user.id}
    )

    if not workspace:
        raise HTTPException(status_code=403, detail="Access denied - owner role required")

    subscriptions_collection = db.subscriptions

    # Update subscription
    result = await subscriptions_collection.update_one(
        {"workspace_id": workspace_id},
        {"$set": {"plan": new_plan, "updated_at": datetime.utcnow()}},
    )

    if result.matched_count == 0:
        # Create new subscription if doesn't exist
        subscription = {
            "workspace_id": workspace_id,
            "plan": new_plan,
            "status": "active",
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "current_period_start": datetime.utcnow(),
            "current_period_end": datetime.utcnow() + timedelta(days=30),
            "cancel_at_period_end": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await subscriptions_collection.insert_one(subscription)

    # Update usage limits
    usage_collection = db.usage_metrics
    await usage_collection.update_one(
        {
            "workspace_id": workspace_id,
            "period_start": {"$gte": datetime.utcnow() - timedelta(days=30)},
        },
        {"$set": {"limits": PLAN_LIMITS[new_plan].model_dump(), "updated_at": datetime.utcnow()}},
    )

    return {
        "message": f"Subscription upgraded to {new_plan}",
        "new_limits": PLAN_LIMITS[new_plan].model_dump(),
    }
