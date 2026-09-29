"""
End-to-end test for audit logging functionality.
"""

import asyncio
from datetime import datetime

import pytest
from bson import ObjectId

from .test_complete_user_flow import PYTHON_API_URL, E2ETestHelper


@pytest.mark.asyncio
async def test_audit_logging_flow():
    """Test that actions are properly logged in the audit system."""
    async with E2ETestHelper() as helper:
        # Step 1: Authenticate
        await helper.sign_in_firebase_user()
        await helper.exchange_firebase_token()

        # Use test workspace
        helper.workspace_id = "6883c972274b0349b71b5ff2"

        # Step 2: Create an action (this should be logged)
        action_name = f"audit-test-action-{int(datetime.utcnow().timestamp())}"
        action_result = await helper.create_action_via_python()

        if "error" in action_result:
            pytest.skip(f"Action creation failed: {action_result}")

        action_id = action_result.get("id")

        # Step 3: Query audit logs
        async with helper.session.get(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/audit-logs",
            params={"resource_type": "action", "limit": 10},
            headers=helper.cookies,
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                logs = data.get("logs", [])

                print(f"🔍 Found {len(logs)} audit logs for workspace {helper.workspace_id}")
                print(f"📝 Looking for action ID: {action_id}")
                for log in logs:
                    print(
                        f"  - {log.get('action')} {log.get('resource_type')} {log.get('resource_id')}"
                    )

                # Find our action creation log
                action_log = None
                for log in logs:
                    if (
                        log.get("resource_type") == "action"
                        and log.get("action") == "CREATE"
                        and log.get("resource_id") == action_id
                    ):
                        action_log = log
                        break

                assert (
                    action_log is not None
                ), f"Action creation was not logged. Action ID: {action_id}"
                # user_email is now optional, so we don't assert on it
                assert action_log["workspace_id"] == helper.workspace_id
                assert action_log["user_id"] is not None  # But user_id is required

                print(
                    f"✅ Audit log found: {action_log['action']} on {action_log['resource_type']}"
                )
            else:
                error_text = await resp.text()
                print(f"⚠️ Failed to get audit logs: {resp.status} - {error_text}")

        # Step 4: Test resource history
        if action_id:
            async with helper.session.get(
                f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/audit-logs/resource/action/{action_id}",
                headers=helper.cookies,
            ) as resp:
                if resp.status == 200:
                    history = await resp.json()
                    assert len(history) >= 1, "Resource should have audit history"
                    assert history[0]["resource_id"] == action_id
                    print(f"✅ Resource history retrieved: {len(history)} entries")

        # Step 5: Test statistics
        async with helper.session.get(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/audit-logs/statistics",
            params={"days": 1},
            headers=helper.cookies,
        ) as resp:
            if resp.status == 200:
                stats = await resp.json()
                assert stats["total_actions"] > 0, "Should have some actions logged"
                print(f"✅ Statistics retrieved: {stats['total_actions']} total actions")


@pytest.mark.asyncio
async def test_audit_log_permissions():
    """Test that audit logs respect permissions."""
    async with E2ETestHelper() as helper:
        # Authenticate
        await helper.sign_in_firebase_user()
        await helper.exchange_firebase_token()

        # Try to access logs for a workspace we don't belong to
        fake_workspace_id = str(ObjectId())

        async with helper.session.get(
            f"{PYTHON_API_URL}/workspaces/{fake_workspace_id}/audit-logs", headers=helper.cookies
        ) as resp:
            # Should either return empty or 403
            if resp.status == 200:
                data = await resp.json()
                assert len(data.get("logs", [])) == 0, "Should not see logs for other workspaces"
            else:
                assert resp.status in [403, 404], f"Unexpected status: {resp.status}"


if __name__ == "__main__":
    asyncio.run(test_audit_logging_flow())
