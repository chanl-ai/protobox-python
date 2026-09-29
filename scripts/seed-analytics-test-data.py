#!/usr/bin/env python3
"""Script to seed test data for analytics using the API."""

import sys
import os
import asyncio
import httpx
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any

# Add the server src to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server', 'src'))

from protobox.admin.utils.mock_data import generate_mock_executions, generate_mock_actions


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Get authentication token for test user."""
    response = await client.post(
        "/admin/api/v1/auth/exchange",
        json={"firebase_token": "test-user123"}
    )
    if response.status_code != 200:
        raise Exception(f"Failed to get auth token: {response.text}")
    return response.json()["access_token"]


async def get_or_create_workspace(client: httpx.AsyncClient, headers: dict, workspace_id: str = None) -> str:
    """Get existing workspace or create a test workspace."""
    # If workspace_id is provided, verify it exists
    if workspace_id:
        response = await client.get(
            "/admin/api/v1/workspaces",
            headers=headers
        )
        if response.status_code == 200:
            workspaces = response.json()
            for ws in workspaces:
                if ws["id"] == workspace_id:
                    print(f"Using existing workspace: {ws['name']} ({workspace_id})")
                    return workspace_id
        print(f"Warning: Workspace {workspace_id} not found, creating new one...")
    
    # Create a new test workspace
    response = await client.post(
        "/admin/api/v1/workspaces",
        headers=headers,
        json={
            "name": "Test Analytics Workspace",
            "slug": f"test-analytics-{random.randint(1000, 9999)}",
            "description": "Workspace for analytics testing with sample data"
        }
    )
    
    if response.status_code == 200:
        return response.json()["id"]
    elif response.status_code == 409:
        # Workspace might already exist, get it
        response = await client.get(
            "/admin/api/v1/workspaces",
            headers=headers
        )
        workspaces = response.json()
        for ws in workspaces:
            if ws["name"] == "Test Analytics Workspace":
                return ws["id"]
        # Create with different name
        response = await client.post(
            "/admin/api/v1/workspaces",
            headers=headers,
            json={
                "name": f"Test Analytics Workspace {random.randint(100, 999)}",
                "slug": f"test-analytics-{random.randint(10000, 99999)}",
                "description": "Workspace for analytics testing with sample data"
            }
        )
        return response.json()["id"]
    else:
        raise Exception(f"Failed to create workspace: {response.text}")


async def create_test_actions(
    client: httpx.AsyncClient, 
    headers: dict, 
    workspace_id: str,
    count: int = 10
) -> List[str]:
    """Create test actions."""
    action_ids = []
    action_types = ["REST_API", "DATABASE", "CODE", "AI", "INTEGRATION"]
    action_names = [
        "fetchUserData", "queryWorkspaces", "executeScript", "generateInsights",
        "syncExternalData", "processWebhook", "runAnalytics", "trainModel",
        "sendNotification", "updateCache"
    ]
    
    for i in range(min(count, len(action_names))):
        action_type = action_types[i % len(action_types)]
        response = await client.post(
            f"/admin/api/v1/actions",
            headers=headers,
            json={
                "workspace_id": workspace_id,
                "name": action_names[i],
                "action_type": action_type,
                "description": f"Test {action_type.lower().replace('_', ' ')} action",
                "status": "active",
                "config": {
                    "timeout": random.choice([30, 60, 120]),
                    "retries": random.choice([0, 1, 3])
                }
            }
        )
        
        if response.status_code == 200:
            action_ids.append(response.json()["id"])
        else:
            print(f"Warning: Failed to create action {action_names[i]}: {response.text}")
    
    return action_ids


async def create_test_executions(
    client: httpx.AsyncClient,
    headers: dict,
    workspace_id: str,
    action_ids: List[str],
    days: int = 7,
    executions_per_day: int = 50
):
    """Create test executions."""
    now = datetime.utcnow()
    
    for day in range(days):
        date = now - timedelta(days=day)
        daily_executions = random.randint(30, executions_per_day)
        
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
            
            execution_data = {
                "workspace_id": workspace_id,
                "action_id": random.choice(action_ids),
                "status": "error" if is_error else "success",
                "duration_ms": duration_ms,
                "created_at": execution_time.isoformat(),
                "metadata": {
                    "request_size": random.randint(100, 10000),
                    "response_size": random.randint(100, 50000)
                }
            }
            
            if is_error:
                execution_data["error"] = {
                    "message": random.choice([
                        "Connection timeout",
                        "Invalid parameters",
                        "Rate limit exceeded",
                        "Internal server error",
                        "Authentication failed"
                    ]),
                    "code": random.choice(["TIMEOUT", "INVALID_PARAMS", "RATE_LIMIT", "INTERNAL", "AUTH"])
                }
            
            # Note: You would need an executions endpoint to actually create these
            # For now, this is a placeholder showing the structure
            # In reality, executions are typically created by actual action runs
            print(f"Would create execution: {execution_data['status']} at {execution_time}")


async def main(workspace_id: str = None):
    """Main function to seed test data.
    
    Args:
        workspace_id: Optional workspace ID to use. If not provided, creates a new workspace.
    """
    base_url = "http://localhost:8090"
    
    print("Seeding analytics test data...")
    print(f"Connecting to {base_url}")
    
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        try:
            # Get auth token
            print("Getting authentication token...")
            token = await get_auth_token(client)
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get or create workspace
            print("Setting up workspace...")
            workspace_id = await get_or_create_workspace(client, headers, workspace_id)
            print(f"Using workspace: {workspace_id}")
            
            # Create actions
            print("Creating test actions...")
            action_ids = await create_test_actions(client, headers, workspace_id, count=10)
            print(f"Created {len(action_ids)} actions")
            
            # Note: Creating executions would require an endpoint that doesn't exist yet
            # Executions are typically created by actual action runs
            print("\nNote: Executions are typically created by running actions.")
            print("To populate execution data, you would need to:")
            print("1. Run the created actions through their execution endpoint")
            print("2. Or use a development endpoint to directly create execution records")
            print("\nFor now, the analytics endpoints will work with any existing execution data.")
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    print("\nTest data seeding complete!")
    print(f"You can now test the analytics endpoints with workspace_id: {workspace_id}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed test data for analytics")
    parser.add_argument("--workspace-id", help="Workspace ID to use (optional)")
    args = parser.parse_args()
    
    asyncio.run(main(args.workspace_id))