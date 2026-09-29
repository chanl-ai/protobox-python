"""Analytics router for dashboard metrics and aggregations."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel

from ..auth.dependencies import require_authentication
from ..auth.models import User
from ..database.connection import DatabaseConnection, get_database_connection
from .workspace import get_current_user as get_workspace_user

router = APIRouter(prefix="/workspaces/{workspace_id}/analytics", tags=["analytics"])

# Constants
MAX_RECENT_ACTIVITY_LIMIT = 100
DEFAULT_RECENT_ACTIVITY_LIMIT = 10
MAX_TOP_ACTIONS_LIMIT = 50
DEFAULT_TOP_ACTIONS_LIMIT = 5
VALID_TIME_RANGES = ["24h", "7d", "30d", "90d"]
DEFAULT_TIME_RANGE = "7d"

# Error rate threshold for alerts (percentage)
ERROR_RATE_WARNING_THRESHOLD = 5.0
ERROR_RATE_CRITICAL_THRESHOLD = 10.0


class TimeRange(BaseModel):
    """Time range for analytics queries."""

    start: datetime
    end: datetime


class ExecutionMetrics(BaseModel):
    """Execution metrics response."""

    total_executions: int
    total_errors: int
    success_rate: float
    avg_response_time: float
    executions_by_date: list[dict[str, Any]]
    errors_by_date: list[dict[str, Any]]


class DashboardStats(BaseModel):
    """Dashboard statistics response."""

    total_executions: int
    active_users: int
    avg_response_time: float
    success_rate: float
    execution_change: float
    user_change: float
    response_time_change: float
    success_rate_change: float


class RecentActivity(BaseModel):
    """Recent activity item."""

    action_name: str
    action_type: str
    description: str
    status: str
    time: datetime
    duration: float
    execution_id: str


def parse_time_range(time_range: str) -> TimeRange:
    """Parse time range string to datetime objects.

    Args:
        time_range: Time range string (24h, 7d, 30d, 90d)

    Returns:
        TimeRange object with start and end dates

    Raises:
        ValueError: If time_range is invalid
    """
    if time_range not in VALID_TIME_RANGES:
        raise ValueError(f"Invalid time range. Must be one of: {', '.join(VALID_TIME_RANGES)}")

    now = datetime.utcnow()

    time_deltas = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
    }

    start = now - time_deltas[time_range]
    return TimeRange(start=start, end=now)


@router.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_stats(
    workspace_id: str,  # Path parameter from router prefix
    time_range: str = Query(
        DEFAULT_TIME_RANGE,
        regex=f"^({'|'.join(VALID_TIME_RANGES)})$",
        description="Time range: 24h, 7d, 30d, 90d",
    ),
    current_user: str = Depends(get_workspace_user),
    db_connection: DatabaseConnection = Depends(get_database_connection),
):
    """Get dashboard statistics with period comparison.

    Returns aggregated metrics with comparison to previous period.
    """
    try:
        db = db_connection.database

        # Parse time range
        period = parse_time_range(time_range)

        # Calculate previous period for comparison
        period_duration = period.end - period.start
        prev_period = TimeRange(start=period.start - period_duration, end=period.start)

        # Build base query - workspace_id is always provided via path parameter
        base_query = {"workspace_id": workspace_id}

        # Current period queries
        current_query = {**base_query, "created_at": {"$gte": period.start, "$lte": period.end}}

        # Previous period queries
        prev_query = {
            **base_query,
            "created_at": {"$gte": prev_period.start, "$lte": prev_period.end},
        }

        # Get execution metrics
        executions = db.executions

        # Current period metrics
        current_executions = await executions.count_documents(current_query)
        current_errors = await executions.count_documents({**current_query, "status": "error"})
        current_success_rate = (
            ((current_executions - current_errors) / current_executions * 100)
            if current_executions > 0
            else 0
        )

        # Average response time (in milliseconds)
        current_avg_response = await executions.aggregate(
            [
                {"$match": current_query},
                {"$group": {"_id": None, "avg_duration": {"$avg": "$duration_ms"}}},
            ]
        ).to_list(1)
        current_avg_response_time = (
            current_avg_response[0].get("avg_duration", 0) if current_avg_response else 0
        )

        # Active users count
        active_users_result = await executions.aggregate(
            [{"$match": current_query}, {"$group": {"_id": "$user_id"}}, {"$count": "count"}]
        ).to_list(1)
        active_users = active_users_result[0].get("count", 0) if active_users_result else 0

        # Previous period metrics for comparison
        prev_executions = await executions.count_documents(prev_query)
        prev_errors = await executions.count_documents({**prev_query, "status": "error"})
        prev_success_rate = (
            ((prev_executions - prev_errors) / prev_executions * 100) if prev_executions > 0 else 0
        )

        prev_avg_response = await executions.aggregate(
            [
                {"$match": prev_query},
                {"$group": {"_id": None, "avg_duration": {"$avg": "$duration_ms"}}},
            ]
        ).to_list(1)
        prev_avg_response_time = (
            prev_avg_response[0].get("avg_duration", 0) if prev_avg_response else 0
        )

        prev_active_users_result = await executions.aggregate(
            [{"$match": prev_query}, {"$group": {"_id": "$user_id"}}, {"$count": "count"}]
        ).to_list(1)
        prev_active_users = (
            prev_active_users_result[0].get("count", 0) if prev_active_users_result else 0
        )

        # Calculate percentage changes
        def calc_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return ((current - previous) / previous) * 100

        return DashboardStats(
            total_executions=current_executions,
            active_users=active_users,
            avg_response_time=round(current_avg_response_time, 2),
            success_rate=round(current_success_rate, 2),
            execution_change=round(calc_change(current_executions, prev_executions), 1),
            user_change=round(calc_change(active_users, prev_active_users), 1),
            response_time_change=round(
                calc_change(current_avg_response_time, prev_avg_response_time), 1
            ),
            success_rate_change=round(current_success_rate - prev_success_rate, 1),
        )

    except ValueError as e:
        logger.error(f"Invalid time range: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard statistics",
        )


@router.get("/execution-metrics", response_model=ExecutionMetrics)
async def get_execution_metrics(
    workspace_id: str,  # Path parameter from router prefix
    time_range: str = Query(
        DEFAULT_TIME_RANGE,
        regex=f"^({'|'.join(VALID_TIME_RANGES)})$",
        description="Time range: 24h, 7d, 30d, 90d",
    ),
    current_user: str = Depends(get_workspace_user),
    db_connection: DatabaseConnection = Depends(get_database_connection),
):
    """Get execution metrics for charts."""
    try:
        db = db_connection.database

        # Parse time range
        period = parse_time_range(time_range)

        # Build base query - workspace_id is always provided via path parameter
        base_query = {"workspace_id": workspace_id}

        query = {**base_query, "created_at": {"$gte": period.start, "$lte": period.end}}

        # Aggregate executions by date
        executions = db.executions

        # Get total metrics
        total_executions = await executions.count_documents(query)
        total_errors = await executions.count_documents({**query, "status": "error"})
        success_rate = (
            ((total_executions - total_errors) / total_executions * 100)
            if total_executions > 0
            else 0
        )

        # Average response time
        avg_response = await executions.aggregate(
            [{"$match": query}, {"$group": {"_id": None, "avg_duration": {"$avg": "$duration_ms"}}}]
        ).to_list(1)
        avg_response_time = avg_response[0].get("avg_duration", 0) if avg_response else 0

        # Group by date for chart data
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                        "status": "$status",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.date": 1}},
        ]

        results = await executions.aggregate(pipeline).to_list(None)

        # Process results into separate series
        date_metrics = {}
        for result in results:
            date = result["_id"]["date"]
            status = result["_id"]["status"]
            count = result["count"]

            if date not in date_metrics:
                date_metrics[date] = {"date": date, "executions": 0, "errors": 0}

            if status == "error":
                date_metrics[date]["errors"] = count
            else:
                date_metrics[date]["executions"] += count

        # Convert to sorted list
        executions_by_date = sorted(date_metrics.values(), key=lambda x: x["date"])

        # Separate errors for chart
        errors_by_date = [
            {"date": item["date"], "errors": item["errors"]} for item in executions_by_date
        ]

        return ExecutionMetrics(
            total_executions=total_executions,
            total_errors=total_errors,
            success_rate=round(success_rate, 2),
            avg_response_time=round(avg_response_time, 2),
            executions_by_date=executions_by_date,
            errors_by_date=errors_by_date,
        )

    except ValueError as e:
        logger.error(f"Invalid time range: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching execution metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch execution metrics",
        )


@router.get("/recent-activity", response_model=list[RecentActivity])
async def get_recent_activity(
    workspace_id: str,  # Path parameter from router prefix
    limit: int = Query(
        DEFAULT_RECENT_ACTIVITY_LIMIT,
        ge=1,
        le=MAX_RECENT_ACTIVITY_LIMIT,
        description="Number of items to return",
    ),
    current_user: str = Depends(get_workspace_user),
    db_connection: DatabaseConnection = Depends(get_database_connection),
):
    """Get recent activity for the dashboard."""
    try:
        db = db_connection.database

        # Build query - workspace_id is always provided via path parameter
        query = {"workspace_id": workspace_id}

        # Get recent executions with action details
        pipeline = [
            {"$match": query},
            {"$sort": {"created_at": -1}},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "actions",
                    "localField": "action_id",
                    "foreignField": "_id",
                    "as": "action",
                }
            },
            {"$unwind": {"path": "$action", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "execution_id": {"$toString": "$_id"},
                    "action_name": {"$ifNull": ["$action.name", "Unknown Action"]},
                    "action_type": {"$ifNull": ["$action.action_type", "unknown"]},
                    "description": {"$ifNull": ["$action.description", "No description"]},
                    "status": 1,
                    "created_at": 1,
                    "duration_ms": 1,
                }
            },
        ]

        executions = db.executions
        results = await executions.aggregate(pipeline).to_list(None)

        # Convert to response model
        activities = []
        for result in results:
            # Map action types to icons
            action_type_map = {
                "REST_API": "api",
                "DATABASE": "database",
                "CODE": "code",
                "AI": "ai",
                "INTEGRATION": "integration",
                "SERVER": "server",
                "COMPUTE": "compute",
                "ML": "ml",
            }

            activities.append(
                RecentActivity(
                    action_name=result["action_name"],
                    action_type=action_type_map.get(result.get("action_type", "unknown"), "api"),
                    description=result.get("description", ""),
                    status=result.get("status", "unknown"),
                    time=result.get("created_at", datetime.utcnow()),
                    duration=result.get("duration_ms", 0) / 1000,  # Convert to seconds
                    execution_id=result["execution_id"],
                )
            )

        return activities

    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch recent activity",
        )


@router.get("/top-actions")
async def get_top_actions(
    workspace_id: str,  # Path parameter from router prefix
    time_range: str = Query(
        DEFAULT_TIME_RANGE,
        regex=f"^({'|'.join(VALID_TIME_RANGES)})$",
        description="Time range: 24h, 7d, 30d, 90d",
    ),
    limit: int = Query(
        DEFAULT_TOP_ACTIONS_LIMIT,
        ge=1,
        le=MAX_TOP_ACTIONS_LIMIT,
        description="Number of top actions",
    ),
    current_user: str = Depends(get_workspace_user),
    db_connection: DatabaseConnection = Depends(get_database_connection),
):
    """Get top performing actions."""
    try:
        db = db_connection.database

        # Parse time range
        period = parse_time_range(time_range)

        # Build query - workspace_id is always provided via path parameter
        query = {
            "workspace_id": workspace_id,
            "created_at": {"$gte": period.start, "$lte": period.end},
        }

        # Aggregate top actions
        pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": "$action_id",
                    "count": {"$sum": 1},
                    "avg_duration": {"$avg": "$duration_ms"},
                    "error_count": {"$sum": {"$cond": [{"$eq": ["$status", "error"]}, 1, 0]}},
                }
            },
            {
                "$lookup": {
                    "from": "actions",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "action",
                }
            },
            {"$unwind": {"path": "$action", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "action_name": {"$ifNull": ["$action.name", "Unknown"]},
                    "action_type": {"$ifNull": ["$action.action_type", "unknown"]},
                    "count": 1,
                    "avg_duration": {"$round": ["$avg_duration", 2]},
                    "error_rate": {"$multiply": [{"$divide": ["$error_count", "$count"]}, 100]},
                }
            },
            {"$sort": {"count": -1}},
            {"$limit": limit},
        ]

        executions = db.executions
        return await executions.aggregate(pipeline).to_list(None)


    except ValueError as e:
        logger.error(f"Invalid time range: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching top actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch top actions"
        )
