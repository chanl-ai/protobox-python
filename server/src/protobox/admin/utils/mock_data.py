"""Mock data generator for development and testing."""

import random
from datetime import datetime, timedelta
from typing import Any

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
                "metadata": {
                    "request_size": random.randint(100, 10000),
                    "response_size": random.randint(100, 50000),
                    "ip_address": f"192.168.1.{random.randint(1, 255)}",
                },
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
    # Use ActionType enum values that match the model
    action_types = ["REST", "O3", "DATABASE", "CODE_RUN"]
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
            "type": action_type,  # Changed from action_type to type
            "description": f"Automated {action_type.lower().replace('_', ' ')} operation",
            "status": "active",
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            "updated_at": datetime.utcnow(),
            "created_by": user_id,  # Add required field
            "version": "1.0.0",  # Add default version
            "tags": [],  # Add empty tags
            "config_schema": {},  # Add empty config schema
            "default_config": {},  # Add empty default config
            "secret_refs": [],  # Add empty secret refs
            "is_builtin": False,  # Add default is_builtin
        }
        actions.append(action)

    return actions


def seed_mock_data(db, user_id: str, workspace_id: str):
    """Seed database with mock data for development."""
    # Generate and insert actions
    actions = generate_mock_actions(user_id, workspace_id)
    if actions:
        db.actions.insert_many(actions)

    # Generate and insert executions
    executions = generate_mock_executions(user_id, workspace_id, days=30)
    if executions:
        # Update executions with real action IDs
        for i, execution in enumerate(executions):
            execution["action_id"] = actions[i % len(actions)]["_id"]

        db.executions.insert_many(executions)

    return {"actions_created": len(actions), "executions_created": len(executions)}
