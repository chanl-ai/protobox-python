"""
End-to-end test for audit logging of CRUD operations.
"""

import asyncio

import pytest

from .test_complete_user_flow import PYTHON_API_URL, E2ETestHelper


@pytest.mark.asyncio
async def test_audit_crud_operations():
    """Test that CREATE, UPDATE, and DELETE operations are properly logged."""
    async with E2ETestHelper() as helper:
        # Step 1: Authenticate
        await helper.sign_in_firebase_user()
        await helper.exchange_firebase_token()

        # Use test workspace
        helper.workspace_id = "6883c972274b0349b71b5ff2"

        # Step 2: Create an action
        action_result = await helper.create_action_via_python()

        if "error" in action_result:
            pytest.skip(f"Action creation failed: {action_result}")

        action_id = action_result.get("id")
        print(f"📦 Created action: {action_id}")

        # Step 3: Update the action
        update_data = {
            "description": "Updated description for audit test",
            "tags": ["audit", "test", "updated"],
        }

        async with helper.session.put(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/actions/{action_id}",
            json=update_data,
            headers=helper.cookies,
        ) as resp:
            if resp.status == 200:
                update_result = await resp.json()
                print(f"✏️ Updated action: {action_id}")
            else:
                error_text = await resp.text()
                print(f"⚠️ Failed to update action: {resp.status} - {error_text}")

        # Step 4: Delete the action
        async with helper.session.delete(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/actions/{action_id}",
            headers=helper.cookies,
        ) as resp:
            if resp.status == 204:
                print(f"🗑️ Deleted action: {action_id}")
            else:
                error_text = await resp.text()
                print(f"⚠️ Failed to delete action: {resp.status} - {error_text}")

        # Step 5: Query audit logs for all operations
        await asyncio.sleep(0.5)  # Give a moment for logs to be written

        # Query audit logs - note: resource_id filtering is not supported in get_logs
        # We'll get all action logs and filter client-side
        async with helper.session.get(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/audit-logs",
            params={"resource_type": "action", "limit": 50},
            headers=helper.cookies,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                logs = data.get("logs", [])

                print(f"🔍 Found {len(logs)} total audit logs")

                # Debug: Print all logs
                for log in logs:
                    print(
                        f"  - {log.get('action')} {log.get('resource_type')} {log.get('resource_id')}"
                    )

                # Check for each operation
                operations = {"CREATE": False, "UPDATE": False, "DELETE": False}

                for log in logs:
                    if log.get("resource_id") == action_id:
                        action = log.get("action")
                        if action in operations:
                            operations[action] = True
                            print(f"  ✓ Found {action} operation for our action {action_id}")

                        # Verify metadata
                        metadata = log.get("metadata", {})
                        assert "action_name" in metadata, f"{action} log missing action_name"
                        assert "action_type" in metadata, f"{action} log missing action_type"

                        # Verify changes for UPDATE
                        if action == "UPDATE":
                            changes = log.get("changes", {})
                            assert "description" in changes, "UPDATE log missing description change"
                            assert "tags" in changes, "UPDATE log missing tags change"

                # Verify all operations were logged
                for op, found in operations.items():
                    assert found, f"{op} operation was not logged"

                print("✅ All CRUD operations were properly audited")
            else:
                error_text = await resp.text()
                print(f"⚠️ Failed to get audit logs: {resp.status} - {error_text}")
                pytest.fail("Failed to retrieve audit logs")


@pytest.mark.asyncio
async def test_audit_log_filtering():
    """Test audit log filtering by various parameters."""
    async with E2ETestHelper() as helper:
        # Authenticate
        await helper.sign_in_firebase_user()
        await helper.exchange_firebase_token()

        helper.workspace_id = "6883c972274b0349b71b5ff2"

        # Create multiple actions for testing
        action_ids = []
        for i in range(3):
            action_result = await helper.create_action_via_python()
            if "id" in action_result:
                action_ids.append(action_result["id"])

        print(f"📦 Created {len(action_ids)} test actions")

        # Test filtering by action type
        async with helper.session.get(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/audit-logs",
            params={"action": "CREATE", "limit": 100},
            headers=helper.cookies,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                logs = data.get("logs", [])

                # All logs should be CREATE actions
                for log in logs:
                    assert (
                        log.get("action") == "CREATE"
                    ), f"Found non-CREATE action: {log.get('action')}"

                print(f"✅ Action filter working: found {len(logs)} CREATE operations")

        # Test filtering by resource type
        async with helper.session.get(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/audit-logs",
            params={"resource_type": "action", "limit": 100},
            headers=helper.cookies,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                logs = data.get("logs", [])

                # All logs should be for action resources
                for log in logs:
                    assert (
                        log.get("resource_type") == "action"
                    ), f"Found non-action resource: {log.get('resource_type')}"

                print(f"✅ Resource type filter working: found {len(logs)} action resources")

        # Clean up created actions
        for action_id in action_ids:
            async with helper.session.delete(
                f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/actions/{action_id}",
                headers=helper.cookies,
            ) as resp:
                pass  # Ignore errors during cleanup


if __name__ == "__main__":
    asyncio.run(test_audit_crud_operations())
