#!/usr/bin/env python3
"""Script to seed sample data directly into a workspace via MongoDB."""

import sys
import os
import asyncio
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import argparse

# Add the server src to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server', 'src'))

from protobox.admin.utils.mock_data import generate_mock_executions, generate_mock_actions


async def seed_workspace_directly(workspace_id: str, user_id: str = None):
    """Seed data directly into MongoDB for a workspace."""
    
    # MongoDB connection - use environment variables if available
    mongo_url = os.getenv("MONGODB_URL", "mongodb://mcp_admin:mcp_dev_password_2024@localhost:27847/mcp_server")
    client = AsyncIOMotorClient(mongo_url)
    db = client.mcp_server
    
    try:
        # Convert workspace_id to ObjectId if it's a string
        workspace_oid = ObjectId(workspace_id)
        
        # Check if workspace exists
        workspace = await db.workspaces.find_one({"_id": workspace_oid})
        if not workspace:
            print(f"Error: Workspace {workspace_id} not found!")
            return
        
        print(f"Found workspace: {workspace['name']}")
        
        # Use the workspace's user_id if not provided
        if not user_id:
            user_id = workspace.get("user_id", "test-user123")
        
        # Generate mock actions
        print("Generating mock actions...")
        actions = generate_mock_actions(user_id, workspace_id, count=15)
        
        # Check if actions already exist
        existing_actions = await db.actions.count_documents({"workspace_id": workspace_id})
        if existing_actions > 0:
            print(f"Found {existing_actions} existing actions, using them for executions")
            # Get existing action IDs for executions
            cursor = db.actions.find({"workspace_id": workspace_id})
            actions = await cursor.to_list(length=100)
        else:
            # Make action names unique by adding random suffix
            timestamp = datetime.utcnow().strftime("%H%M%S")
            for action in actions:
                action["name"] = f"{action['name']}_{timestamp}"
                # Add created_by field to avoid unique constraint issues
                action["created_by"] = user_id
            
            # Insert actions
            try:
                result = await db.actions.insert_many(actions)
                print(f"Created {len(result.inserted_ids)} actions")
            except Exception as e:
                print(f"Warning: Could not create actions: {e}")
                # Try to get any existing actions
                cursor = db.actions.find({"workspace_id": workspace_id})
                actions = await cursor.to_list(length=100)
                if not actions:
                    print("No actions available, skipping execution creation")
                    return
        
        # Generate mock executions
        print("Generating mock executions...")
        executions = generate_mock_executions(
            user_id, 
            workspace_id, 
            days=30,  # 30 days of data
            executions_per_day=50  # Average 50 executions per day
        )
        
        # Assign real action IDs to executions
        if actions:
            for i, execution in enumerate(executions):
                execution["action_id"] = str(actions[i % len(actions)]["_id"])
                # Also store action details for display
                action = actions[i % len(actions)]
                execution["action_name"] = action["name"]
                execution["action_type"] = action.get("type", "REST")
        
        # Check existing executions
        existing_executions = await db.executions.count_documents({"workspace_id": workspace_id})
        if existing_executions > 0:
            print(f"Found {existing_executions} existing executions")
            response = input("Do you want to add more executions? (y/n): ")
            if response.lower() != 'y':
                print("Skipping execution creation")
                return
        
        # Insert executions
        result = await db.executions.insert_many(executions)
        print(f"Created {len(result.inserted_ids)} executions")
        
        # Create some recent activity for "Recent Activity" section
        print("Creating recent activity...")
        now = datetime.utcnow()
        recent_executions = []
        
        for i in range(10):  # Last 10 activities
            minutes_ago = i * 5  # Every 5 minutes
            execution_time = now - timedelta(minutes=minutes_ago)
            
            action = random.choice(actions)
            is_error = random.random() < 0.1  # 10% error rate for recent
            
            recent = {
                "_id": ObjectId(),
                "user_id": user_id,
                "workspace_id": workspace_id,
                "action_id": str(action["_id"]),
                "action_name": action["name"],
                "action_type": action.get("type", "REST"),
                "status": "error" if is_error else "success",
                "duration_ms": random.gauss(200, 50) if not is_error else random.gauss(1200, 300),
                "created_at": execution_time,
                "updated_at": execution_time,
                "metadata": {
                    "request_size": random.randint(100, 5000),
                    "response_size": random.randint(100, 20000),
                    "ip_address": f"192.168.1.{random.randint(1, 255)}"
                }
            }
            
            if is_error:
                recent["error"] = {
                    "message": random.choice([
                        "Connection timeout",
                        "Rate limit exceeded",
                        "Invalid response"
                    ]),
                    "code": random.choice(["TIMEOUT", "RATE_LIMIT", "INVALID"])
                }
            
            recent_executions.append(recent)
        
        # Insert recent executions
        result = await db.executions.insert_many(recent_executions)
        print(f"Created {len(result.inserted_ids)} recent executions")
        
        print("\n✅ Successfully seeded data!")
        print(f"Workspace ID: {workspace_id}")
        print(f"- Actions: {len(actions)}")
        print(f"- Total Executions: {len(executions) + len(recent_executions)}")
        print("\nYou should now see data in your dashboard!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


async def main():
    parser = argparse.ArgumentParser(description="Seed sample data into a workspace")
    parser.add_argument("workspace_id", help="Workspace ID to seed data into")
    parser.add_argument("--user-id", help="User ID (optional, will use workspace owner)")
    args = parser.parse_args()
    
    await seed_workspace_directly(args.workspace_id, args.user_id)


if __name__ == "__main__":
    asyncio.run(main())