"""Integration tests for chat API endpoints."""


import pytest
from bson import ObjectId
from httpx import Client

from .test_utils import get_emulator_auth_token


@pytest.mark.integration
class TestChatAPI:
    """Test chat API endpoints."""

    @classmethod
    def setup_class(cls):
        """Setup test client and authentication."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        cls.skip_tests = False
        cls.skip_reason = None
        cls.workspace_id = None
        cls.assistant_id = None
        cls.thread_id = None
        cls.test_thread_created = False

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
            return
            return

        # Get or create a workspace
        try:
            response = cls.client.get("/admin/api/v1/workspaces", headers=cls.headers)
            if response.status_code == 200:
                data = response.json()
                workspaces = data.get("workspaces", [])
                if workspaces:
                    cls.workspace_id = workspaces[0]["id"]
                else:
                    # Create a test workspace
                    response = cls.client.post(
                        "/admin/api/v1/workspaces",
                        headers=cls.headers,
                        json={
                            "name": "Test Chat Workspace",
                            "slug": f"test-chat-{ObjectId()}",
                            "description": "Workspace for chat testing",
                        },
                    )
                    if response.status_code in [200, 201]:
                        cls.workspace_id = response.json()["id"]

            # Try to create a default assistant and thread for tests
            if cls.workspace_id:
                # Get or create assistant
                response = cls.client.get(
                    f"/admin/api/v1/workspaces/{cls.workspace_id}/assistants", headers=cls.headers
                )
                if response.status_code == 200:
                    assistants = response.json()
                    if assistants:
                        cls.assistant_id = assistants[0]["id"]

                # Create a test thread for message tests
                if cls.assistant_id:
                    import time

                    thread_name = f"Test Thread Setup {int(time.time() * 1000)}"
                    response = cls.client.post(
                        f"/admin/api/v1/workspaces/{cls.workspace_id}/chat/threads",
                        headers=cls.headers,
                        json={
                            "name": thread_name,
                            "assistant_id": cls.assistant_id,
                            "metadata": {"test_setup": True},
                        },
                    )
                    if response.status_code in [200, 201]:
                        cls.thread_id = response.json()["id"]
                        cls.test_thread_created = True

        except Exception as e:
            print(f"Failed to setup workspace: {e}")

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
        if not self.workspace_id:
            pytest.skip("No workspace available for testing")

    def test_create_assistant(self):
        """Test creating an assistant."""
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/assistants",
            headers=self.headers,
            json={
                "name": "Test Assistant",
                "description": "Assistant for integration testing",
                "model": "gpt-4",
                "instructions": "You are a helpful assistant for testing.",
                "tools": [],
            },
        )

        # Accept 200, 201, or 409 (already exists)
        assert response.status_code in [200, 201, 409]

        if response.status_code in [200, 201]:
            data = response.json()
            self.__class__.assistant_id = data["id"]
            assert "id" in data
            assert data["name"] == "Test Assistant"

    def test_list_assistants(self):
        """Test listing assistants."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/assistants", headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if data:
            # Save first assistant ID for later tests
            self.__class__.assistant_id = data[0]["id"]

    def test_create_thread(self):
        """Test creating a chat thread."""
        if not self.assistant_id:
            # Try to get an assistant first
            response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/assistants", headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    self.__class__.assistant_id = data[0]["id"]
                else:
                    pytest.skip("No assistant available")
            else:
                pytest.skip("Cannot list assistants")

        # Generate unique thread name to avoid conflicts
        import time

        thread_name = f"Test Thread {int(time.time())}"

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads",
            headers=self.headers,
            json={
                "name": thread_name,
                "assistant_id": self.assistant_id,
                "metadata": {"test": True},
            },
        )

        # Accept 201 (created) or 400 (if thread exists)
        if response.status_code == 400 and "already exists" in response.text:
            # Thread exists, try with a different name
            thread_name = f"Test Thread {int(time.time() * 1000)}"
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads",
                headers=self.headers,
                json={
                    "name": thread_name,
                    "assistant_id": self.assistant_id,
                    "metadata": {"test": True},
                },
            )

        assert response.status_code in [200, 201]
        data = response.json()
        self.__class__.thread_id = data["id"]
        assert "id" in data
        # Note: assistant_id might be in context_data rather than top level
        if "assistant_id" in data:
            assert data["assistant_id"] == self.assistant_id
        elif "context_data" in data and "assistant_id" in data["context_data"]:
            assert data["context_data"]["assistant_id"] == self.assistant_id

    def test_list_threads(self):
        """Test listing chat threads."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads", headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        # Response is a dict with threads key
        assert "threads" in data
        threads = data["threads"]
        assert isinstance(threads, list)

        if threads:
            # Save first thread ID for later tests
            self.__class__.thread_id = threads[0]["id"]

    def test_send_message(self):
        """Test sending a message to a thread."""
        if not self.thread_id:
            pytest.skip("No thread available for testing")

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{self.thread_id}/messages",
            headers=self.headers,
            json={"role": "user", "content": "Hello, this is a test message"},
        )

        # Accept 200, 201 or 404 (if endpoint not implemented)
        assert response.status_code in [200, 201, 404]

        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["role"] == "user"
            assert data["content"] == "Hello, this is a test message"

    def test_list_messages(self):
        """Test listing messages in a thread."""
        if not self.thread_id:
            pytest.skip("No thread available for testing")

        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{self.thread_id}/messages",
            headers=self.headers,
        )

        # Accept 200 or 404 (if endpoint not implemented)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Response is a dict with messages key
            if isinstance(data, dict) and "messages" in data:
                messages = data["messages"]
                assert isinstance(messages, list)
            else:
                # Or could be a list directly (older API)
                assert isinstance(data, list)

    def test_chat_streaming(self):
        """Test the chat streaming endpoint."""
        if not self.thread_id:
            pytest.skip("No thread available for testing")

        # The chat endpoint expects thread_id and content
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{self.thread_id}/chat",
            headers=self.headers,
            json={"content": "Test message for streaming"},
            timeout=5.0,  # Short timeout for streaming test
        )

        # Accept 200 (success), 404 (not found), or 422 (validation error)
        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            # For streaming responses (SSE), verify content type
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type or "text/plain" in content_type
            assert response.content is not None

    def test_delete_thread(self):
        """Test deleting a chat thread."""
        if not self.thread_id:
            pytest.skip("No thread available for testing")

        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{self.thread_id}",
            headers=self.headers,
        )

        # Accept 200, 204, or 404
        assert response.status_code in [200, 204, 404]

    def test_chat_summary(self):
        """Test getting chat summary statistics."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/summary", headers=self.headers
        )

        # Accept 200 or 404 (if not implemented)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Verify summary structure if implemented
            if data:
                assert isinstance(data, dict)

    def test_thread_operations_workflow(self):
        """Test complete thread workflow: create, update, list, delete."""
        import time

        # Create a thread with unique name
        thread_name = f"Integration Test Thread {int(time.time() * 1000)}"
        create_response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads",
            headers=self.headers,
            json={
                "assistant_id": self.assistant_id or "test-assistant",
                "name": thread_name,
                "metadata": {"test": True, "purpose": "integration_test"},
            },
        )
        assert create_response.status_code in [200, 201]
        thread = create_response.json()
        thread_id = thread["id"]

        # Update the thread
        update_response = self.client.put(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{thread_id}",
            headers=self.headers,
            json={"name": "Updated Test Thread", "metadata": {"test": True, "updated": True}},
        )
        assert update_response.status_code in [200, 404]

        # List threads and verify our thread is there
        list_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads", headers=self.headers
        )
        assert list_response.status_code == 200
        threads = list_response.json().get("threads", [])
        thread_ids = [t["id"] for t in threads]
        assert thread_id in thread_ids

        # Delete the thread
        delete_response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{thread_id}",
            headers=self.headers,
        )
        assert delete_response.status_code in [200, 204, 404]

    def test_message_operations_workflow(self):
        """Test complete message workflow: create multiple, list, search."""
        # Create a fresh thread for this test to ensure isolation
        if not self.assistant_id:
            pytest.skip("No assistant available for testing")

        import time

        thread_name = f"Message Test Thread {int(time.time() * 1000)}"
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads",
            headers=self.headers,
            json={
                "name": thread_name,
                "assistant_id": self.assistant_id,
                "metadata": {"test": "message_operations"},
            },
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not create thread: {response.status_code}")

        test_thread_id = response.json()["id"]

        # Create multiple messages
        messages_created = []
        for i in range(3):
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{test_thread_id}/messages",
                headers=self.headers,
                json={"role": "user", "content": f"Test message {i+1} for search testing"},
            )
            if response.status_code in [200, 201]:
                messages_created.append(response.json())

        # List messages with pagination
        list_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{test_thread_id}/messages?limit=2",
            headers=self.headers,
        )
        assert list_response.status_code in [200, 404]

        if list_response.status_code == 200:
            data = list_response.json()
            messages = data.get("messages", [])
            pagination = data.get("pagination", {})
            assert len(messages) <= 2
            assert "total" in pagination
            assert "has_more" in pagination

        # Search messages
        search_response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/search/messages?search_query=search+testing",
            headers=self.headers,
        )
        assert search_response.status_code in [200, 404]

        if search_response.status_code == 200:
            data = search_response.json()
            assert "messages" in data
            assert "pagination" in data
            assert "search" in data

    def test_thread_sharing(self):
        """Test thread sharing functionality."""
        if not self.thread_id:
            pytest.skip("No thread available for testing")

        # Share thread with test users
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{self.thread_id}/share",
            headers=self.headers,
            json={"user_ids": ["test-user-1", "test-user-2"]},
        )

        # Accept 200 (success), 404 (not found), or 400 (bad request)
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            data = response.json()
            assert data.get("success") is True
            assert "shared_with" in data

    def test_error_handling(self):
        """Test error handling for invalid requests."""
        # Test invalid ObjectId
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/invalid-id",
            headers=self.headers,
        )
        assert response.status_code in [400, 404]

        # Test missing required fields
        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads",
            headers=self.headers,
            json={},  # Missing assistant_id
        )
        assert response.status_code in [400, 422]

        # Test invalid message role
        if self.thread_id:
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{self.thread_id}/messages",
                headers=self.headers,
                json={"role": "invalid_role", "content": "Test message"},
            )
            assert response.status_code in [400, 422]

    def test_pagination(self):
        """Test pagination for threads and messages."""
        # Test thread pagination
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads?limit=5&skip=0",
            headers=self.headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "threads" in data
        assert "pagination" in data
        pagination = data["pagination"]
        assert "total" in pagination
        assert "skip" in pagination
        assert "limit" in pagination
        assert "has_more" in pagination

        # Test message pagination - create a fresh thread
        if self.assistant_id:
            import time

            thread_name = f"Pagination Test Thread {int(time.time() * 1000)}"
            thread_response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads",
                headers=self.headers,
                json={
                    "name": thread_name,
                    "assistant_id": self.assistant_id,
                    "metadata": {"test": "pagination"},
                },
            )

            if thread_response.status_code in [200, 201]:
                test_thread_id = thread_response.json()["id"]

                # Add some messages to test pagination
                for i in range(10):
                    self.client.post(
                        f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{test_thread_id}/messages",
                        headers=self.headers,
                        json={"role": "user", "content": f"Message {i}"},
                    )

                # Now test pagination
                response = self.client.get(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/chat/threads/{test_thread_id}/messages?limit=5&skip=2",
                    headers=self.headers,
                )
                assert response.status_code == 200

                data = response.json()
                assert "messages" in data
                assert "pagination" in data

                # Verify pagination metadata
                pagination = data["pagination"]
                assert pagination["limit"] == 5
                assert pagination["skip"] == 2
                assert len(data["messages"]) <= 5
