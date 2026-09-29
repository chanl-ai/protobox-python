#!/usr/bin/env python3
"""
UI API Contract Tests
Tests that verify the exact API contract that the UI depends on.
These tests assume a running server on localhost:8090.
"""

import json
import time

import pytest
from httpx import Client

from .test_utils import get_emulator_auth_token


@pytest.mark.integration
class APIContractTestCase:
    """Base test case with common setup and utilities."""

    @classmethod
    def setup_class(cls):
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        cls.workspace_id = "6883c972274b0349b71b5ff2"
        cls.test_action_id = "6883cc77f0dd6dbee6550be8"

        # Check if server is running
        try:
            cls.client.get("/admin/api/v1/health")
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"
            return

        # Get Firebase emulator token
        cls.token, cls.refresh_token, cls.headers = get_emulator_auth_token(cls.client)

        if not cls.token:
            cls.skip_tests = True
            cls.skip_reason = "Authentication not enabled or Firebase emulator not running"
        else:
            cls.skip_tests = False

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def api_request(
        self, method: str, endpoint: str, data: dict | None = None, expected_status: int = 200
    ):
        """Make API request with proper error handling."""

        try:
            if method.upper() == "GET":
                response = self.client.get(f"/admin/api/v1{endpoint}", headers=self.headers)
            elif method.upper() == "POST":
                response = self.client.post(
                    f"/admin/api/v1{endpoint}", json=data, headers=self.headers
                )
            elif method.upper() == "PUT":
                response = self.client.put(
                    f"/admin/api/v1{endpoint}", json=data, headers=self.headers
                )
            elif method.upper() == "DELETE":
                response = self.client.delete(f"/admin/api/v1{endpoint}", headers=self.headers)
            else:
                assert False, f"Unsupported HTTP method: {method}"

            # Check status code
            assert response.status_code == expected_status, (
                f"{method} {endpoint} returned {response.status_code}, expected {expected_status}. "
                f"Response: {response.text[:500]}"
            )

            return response

        except Exception as e:
            assert False, f"API request failed: {method} {endpoint} - {str(e)}"


class TestHealthAndBasics(APIContractTestCase):
    """Test basic health and connectivity."""

    def test_server_health(self):
        """Test server health endpoint returns proper structure."""
        response = self.api_request("GET", "/health")

        data = response.json()

        # Verify required fields
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "components" in data

        # Verify database component
        assert "database" in data["components"]
        db_status = data["components"]["database"]
        assert db_status["status"] == "healthy"
        assert "latency_ms" in db_status
        assert isinstance(db_status["latency_ms"], (int, float))


class TestWorkspaceEndpoints(APIContractTestCase):
    """Test workspace-related endpoints that UI uses."""

    def test_list_workspaces(self):
        """Test listing workspaces returns proper format."""
        response = self.api_request("GET", "/workspaces")

        data = response.json()

        # Should be an object with workspaces array
        assert isinstance(data, dict)
        assert "workspaces" in data
        assert "user" in data

        workspaces = data["workspaces"]
        assert isinstance(workspaces, list)

        if workspaces:
            workspace = workspaces[0]
            # Verify workspace structure
            assert "id" in workspace
            assert "name" in workspace
            assert isinstance(workspace["id"], str)
            assert isinstance(workspace["name"], str)


class TestActionEndpoints(APIContractTestCase):
    """Test action endpoints that UI depends on."""

    def test_list_actions(self):
        """Test listing actions returns proper JSON without ObjectId errors."""
        endpoint = f"/workspaces/{self.workspace_id}/actions"
        response = self.api_request("GET", endpoint)

        actions = response.json()

        # Should be a list
        assert isinstance(actions, list)

        if actions:
            action = actions[0]
            # Verify critical fields for UI
            assert "id" in action
            assert "name" in action
            assert "type" in action
            assert "status" in action

            # Verify types (no ObjectId serialization issues)
            assert isinstance(action["id"], str)
            assert isinstance(action["name"], str)
            assert isinstance(action["type"], str)

            # Verify no MongoDB ObjectId objects
            action_str = json.dumps(action)  # Should not raise serialization error
            assert isinstance(action_str, str)

    def test_get_action_by_id(self):
        """Test getting specific action - the endpoint that was failing."""
        # First, create a test action with unique name

        action_data = {
            "name": f"Test Action for Get By ID {int(time.time())}",
            "description": "A test action for testing get by ID",
            "type": "REST",
            "config": {"url": "https://httpbin.org/get", "method": "GET"},
        }

        # Create the action
        create_endpoint = f"/workspaces/{self.workspace_id}/actions"
        create_response = self.api_request(
            "POST", create_endpoint, data=action_data, expected_status=201
        )
        created_action = create_response.json()
        action_id = created_action["id"]

        # Now test getting the action by ID
        endpoint = f"/workspaces/{self.workspace_id}/actions/{action_id}"
        response = self.api_request("GET", endpoint)

        action = response.json()

        # Verify critical fields
        assert "id" in action
        assert "name" in action
        assert "type" in action
        assert "workspace_id" in action

        # Verify values
        assert action["id"] == action_id
        assert action["workspace_id"] == self.workspace_id
        assert action["name"] == action_data["name"]

        # Verify no ObjectId serialization issues
        assert isinstance(action["id"], str)

        # Should serialize to JSON without errors
        action_json = json.dumps(action)
        assert isinstance(action_json, str)

    def test_get_action_types(self):
        """Test getting action types."""
        response = self.api_request("GET", "/actions/types")

        types = response.json()

        # Should be a list
        assert isinstance(types, list)

        if types:
            action_type = types[0]
            assert "type" in action_type
            assert "description" in action_type

    def test_get_nonexistent_action(self):
        """Test getting action that doesn't exist."""
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
        endpoint = f"/workspaces/{self.workspace_id}/actions/{fake_id}"

        self.api_request("GET", endpoint, expected_status=404)

    def test_get_action_invalid_id(self):
        """Test getting action with invalid ID format."""
        invalid_id = "not-a-valid-objectid"
        endpoint = f"/workspaces/{self.workspace_id}/actions/{invalid_id}"

        self.api_request("GET", endpoint, expected_status=400)


class TestExecutionEndpoints(APIContractTestCase):
    """Test execution endpoints that UI uses."""

    def test_list_executions(self):
        """Test listing executions returns proper format."""
        endpoint = f"/workspaces/{self.workspace_id}/executions"
        response = self.api_request("GET", endpoint)

        executions = response.json()

        # Should be a list
        assert isinstance(executions, list)

        # Should serialize without ObjectId errors
        executions_json = json.dumps(executions)
        assert isinstance(executions_json, str)


class TestChatEndpoints(APIContractTestCase):
    """Test chat endpoints that UI depends on."""

    def test_list_threads(self):
        """Test listing chat threads returns proper format."""
        endpoint = f"/workspaces/{self.workspace_id}/chat/threads"
        response = self.api_request("GET", endpoint)

        data = response.json()

        # Should have threads and pagination
        assert "threads" in data
        assert "pagination" in data

        threads = data["threads"]
        assert isinstance(threads, list)

        pagination = data["pagination"]
        assert "total" in pagination
        assert "skip" in pagination
        assert "limit" in pagination
        assert "has_more" in pagination

    def test_create_thread(self):
        """Test creating a new chat thread."""

        endpoint = f"/workspaces/{self.workspace_id}/chat/threads"
        thread_data = {
            "name": f"Test Chat Thread {time.time()}",  # Unique name
            "description": "Test thread created by API tests",
            "context_data": {"test": True},
        }

        response = self.api_request("POST", endpoint, data=thread_data, expected_status=201)

        thread = response.json()

        # Verify thread structure
        assert "id" in thread
        assert "name" in thread
        assert "status" in thread
        assert "created_at" in thread

        # Store thread ID for cleanup
        self.created_thread_id = thread["id"]

        # Verify types (no ObjectId serialization issues)
        assert isinstance(thread["id"], str)
        assert isinstance(thread["name"], str)

        return thread["id"]

    def test_get_thread(self):
        """Test getting a specific thread."""
        # First create a thread
        thread_id = self.test_create_thread()

        endpoint = f"/workspaces/{self.workspace_id}/chat/threads/{thread_id}"
        response = self.api_request("GET", endpoint)

        thread = response.json()

        # Verify thread data
        assert thread["id"] == thread_id
        assert "name" in thread
        assert "status" in thread

        # Cleanup
        delete_endpoint = f"/workspaces/{self.workspace_id}/chat/threads/{thread_id}"
        self.api_request("DELETE", delete_endpoint, expected_status=204)

    def test_create_message(self):
        """Test creating a message in a thread."""
        # First create a thread
        thread_id = self.test_create_thread()

        endpoint = f"/workspaces/{self.workspace_id}/chat/threads/{thread_id}/messages"
        message_data = {"content": "Test message from API tests", "role": "user"}

        response = self.api_request("POST", endpoint, data=message_data, expected_status=201)

        message = response.json()

        # Verify message structure
        assert "id" in message
        assert "content" in message
        assert "role" in message
        assert "created_at" in message

        # Verify types
        assert isinstance(message["id"], str)
        assert message["role"] == "user"

        # Cleanup
        delete_endpoint = f"/workspaces/{self.workspace_id}/chat/threads/{thread_id}"
        self.api_request("DELETE", delete_endpoint, expected_status=204)

    def test_get_thread_messages(self):
        """Test getting messages from a thread."""
        # First create a thread and message
        thread_id = self.test_create_thread()

        # Create a message
        message_endpoint = f"/workspaces/{self.workspace_id}/chat/threads/{thread_id}/messages"
        message_data = {"content": "Test message", "role": "user"}
        self.api_request("POST", message_endpoint, data=message_data, expected_status=201)

        # Get messages
        endpoint = f"/workspaces/{self.workspace_id}/chat/threads/{thread_id}/messages"
        response = self.api_request("GET", endpoint)

        data = response.json()

        # Should have messages and pagination
        assert "messages" in data
        assert "pagination" in data

        messages = data["messages"]
        assert isinstance(messages, list)
        assert len(messages) > 0

        # Cleanup
        delete_endpoint = f"/workspaces/{self.workspace_id}/chat/threads/{thread_id}"
        self.api_request("DELETE", delete_endpoint, expected_status=204)

    def test_chat_summary(self):
        """Test getting chat summary for workspace."""
        endpoint = f"/workspaces/{self.workspace_id}/chat/summary"
        response = self.api_request("GET", endpoint)

        summary = response.json()

        # Verify summary structure
        assert "total_threads" in summary
        assert "total_messages" in summary
        assert "active_threads" in summary

        # Verify types
        assert isinstance(summary["total_threads"], int)
        assert isinstance(summary["total_messages"], int)


class TestAssistantEndpoints(APIContractTestCase):
    """Test assistant endpoints that UI depends on."""

    def test_list_assistants(self):
        """Test listing assistants returns proper format."""
        endpoint = f"/workspaces/{self.workspace_id}/assistants"
        response = self.api_request("GET", endpoint)

        assistants = response.json()

        # Should be a list
        assert isinstance(assistants, list)

        if assistants:
            assistant = assistants[0]
            # Verify assistant structure
            assert "id" in assistant
            assert "name" in assistant
            assert "model" in assistant
            assert "status" in assistant

            # Verify types
            assert isinstance(assistant["id"], str)
            assert isinstance(assistant["name"], str)

    def test_create_assistant(self):
        """Test creating a new assistant."""
        endpoint = f"/workspaces/{self.workspace_id}/assistants"
        assistant_data = {
            "name": "Test Assistant",
            "instructions": "You are a test assistant",
            "model": "gpt-4-turbo-preview",
            "enable_mcp_tools": False,  # Disabled due to module conflicts
        }

        response = self.api_request(
            "POST", endpoint, data=assistant_data, expected_status=200
        )  # API returns 200, not 201

        assistant = response.json()

        # Verify assistant structure
        assert "id" in assistant
        assert "name" in assistant
        assert "assistant_id" in assistant  # OpenAI ID

        # Store for cleanup
        self.created_assistant_id = assistant["id"]

        # Cleanup
        delete_endpoint = f"/workspaces/{self.workspace_id}/assistants/{assistant['id']}"
        self.api_request("DELETE", delete_endpoint, expected_status=200)  # API returns 200, not 204


class TestErrorHandling(APIContractTestCase):
    """Test error handling and edge cases."""

    def test_nonexistent_workspace(self):
        """Test using nonexistent workspace ID."""
        fake_workspace = "507f1f77bcf86cd799439011"
        endpoint = f"/workspaces/{fake_workspace}/actions"

        response = self.api_request("GET", endpoint, expected_status=200)
        # Should return empty list, not error
        actions = response.json()
        assert isinstance(actions, list)

    def test_invalid_workspace_id(self):
        """Test using invalid workspace ID format."""
        invalid_workspace = "not-valid"
        endpoint = f"/workspaces/{invalid_workspace}/actions"

        # Should handle gracefully
        response = self.api_request("GET", endpoint, expected_status=200)
        actions = response.json()
        assert isinstance(actions, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
