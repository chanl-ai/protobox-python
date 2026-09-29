"""Test fixtures for analytics endpoints."""

import random
from datetime import datetime, timedelta
from typing import Any

import pytest
from bson import ObjectId


def generate_mock_executions(
    user_id: str, workspace_id: str, days: int = 30, executions_per_day: int = 100
) -> list[dict[str, Any]]:
    """Generate mock execution data for testing analytics."""
    executions = []
    action_types = ["REST_API", "DATABASE", "CODE", "AI", "INTEGRATION", "SERVER", "COMPUTE", "ML"]
    action_names = [
        "fetchUserData",
        "queryWorkspaces",
        "executeScript",
        "generateInsights",
        "syncExternalData",
        "processWebhook",
        "runAnalytics",
        "trainModel",
        "sendNotification",
        "updateCache",
        "validateData",
        "exportReport",
    ]

    now = datetime.utcnow()

    for day in range(days):
        date = now - timedelta(days=day)
        daily_executions = random.randint(50, executions_per_day)

        for _ in range(daily_executions):
            # Random time within the day
            hours = random.randint(0, 23)
            minutes = random.randint(0, 59)
            seconds = random.randint(0, 59)

            execution_time = date.replace(hour=hours, minute=minutes, second=seconds)

            # Random execution properties
            is_error = random.random() < 0.05  # 5% error rate
            duration_ms = random.gauss(250, 100) if not is_error else random.gauss(1500, 500)
            duration_ms = max(10, duration_ms)  # Minimum 10ms

            execution = {
                "_id": ObjectId(),
                "user_id": user_id,
                "workspace_id": workspace_id,
                "action_id": ObjectId(),
                "action_name": random.choice(action_names),
                "action_type": random.choice(action_types),
                "status": "error" if is_error else "success",
                "duration_ms": duration_ms,
                "created_at": execution_time,
                "updated_at": execution_time,
            }

            if is_error:
                execution["error"] = {
                    "message": random.choice(
                        [
                            "Connection timeout",
                            "Invalid parameters",
                            "Rate limit exceeded",
                            "Internal server error",
                            "Authentication failed",
                        ]
                    ),
                    "code": random.choice(
                        ["TIMEOUT", "INVALID_PARAMS", "RATE_LIMIT", "INTERNAL", "AUTH"]
                    ),
                }

            executions.append(execution)

    return executions


def generate_mock_actions(user_id: str, workspace_id: str, count: int = 20) -> list[dict[str, Any]]:
    """Generate mock action definitions."""
    action_types = ["REST_API", "DATABASE", "CODE", "AI", "INTEGRATION", "SERVER", "COMPUTE", "ML"]
    action_names = [
        "fetchUserData",
        "queryWorkspaces",
        "executeScript",
        "generateInsights",
        "syncExternalData",
        "processWebhook",
        "runAnalytics",
        "trainModel",
        "sendNotification",
        "updateCache",
        "validateData",
        "exportReport",
        "backupDatabase",
        "cleanupLogs",
        "optimizeQueries",
        "refreshTokens",
    ]

    actions = []
    for i in range(min(count, len(action_names))):
        action_type = action_types[i % len(action_types)]
        action = {
            "_id": ObjectId(),
            "user_id": user_id,
            "workspace_id": workspace_id,
            "name": action_names[i],
            "action_type": action_type,
            "description": f"Automated {action_type.lower().replace('_', ' ')} operation",
            "status": "active",
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            "updated_at": datetime.utcnow(),
        }
        actions.append(action)

    return actions


@pytest.fixture
async def seed_analytics_data():
    """Fixture to seed analytics test data."""
    from motor.motor_asyncio import AsyncIOMotorClient

    # Use the regular MongoDB instance for tests
    client = AsyncIOMotorClient(
        "mongodb://mcp_admin:mcp_dev_password_2024@localhost:27847/mcp_server"
    )
    db = client.mcp_server

    user_id = "test_user_123"
    workspace_id = "test_workspace_123"

    # Clear existing data
    await db.actions.delete_many({"user_id": user_id})
    await db.executions.delete_many({"user_id": user_id})

    # Generate and insert test data
    actions = generate_mock_actions(user_id, workspace_id)
    if actions:
        await db.actions.insert_many(actions)

    executions = generate_mock_executions(user_id, workspace_id, days=30)
    if executions:
        # Update executions with real action IDs
        for i, execution in enumerate(executions):
            execution["action_id"] = actions[i % len(actions)]["_id"]

        await db.executions.insert_many(executions)

    return {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "actions_count": len(actions),
        "executions_count": len(executions),
    }
