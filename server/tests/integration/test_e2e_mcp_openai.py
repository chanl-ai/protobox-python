#!/usr/bin/env python3
"""
End-to-End MCP OpenAI Integration Test (Fail Fast Version)

This test verifies the complete flow:
1. Create a workspace
2. Add actions/tools to the workspace
3. Test MCP tool discovery and execution
4. Verify responses

Uses OpenAI Agents SDK to test MCP server integration.
"""

import asyncio
import os
import sys
import time
import unittest

# Import OpenAI Agents SDK
try:
    from agents import Agent, Runner
    from agents.mcp import MCPServerSse

    OPENAI_AGENTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ OpenAI Agents SDK not available: {e}")
    print("Install with: pip install openai-agents")
    OPENAI_AGENTS_AVAILABLE = False


from httpx import Client

from .test_utils import ensure_test_workspace, get_emulator_auth_token


class E2EMCPOpenAITestCase(unittest.TestCase):
    """End-to-end test case for MCP OpenAI integration."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment with real auth via Firebase emulator."""
        cls.timeout = 30
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)

        # Test configuration
        cls.test_workspace_name = "E2E Test Workspace"
        cls.test_action_name = f"test-echo-action-{int(time.time())}"

        # Set test OpenAI API key (for testing purposes only)
        if not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = "sk-test-key-for-validation-only"
            print("⚠️ Using test OpenAI API key for validation")

        # Verify server is running
        try:
            response = cls.client.get("/admin/api/v1/health")
            if response.status_code != 200:
                raise Exception("Server unhealthy")
        except Exception as e:
            print("❌ Cannot connect to server at http://localhost:8090")
            print(f"Error: {e}")
            print("Make sure to run: make start")
            sys.exit(1)

        print("✅ Server is running and healthy")

        # Auth via emulator
        token, refresh_token, headers = get_emulator_auth_token(cls.client)
        if not token:
            cls.skip_tests = True
            cls.skip_reason = "Authentication not enabled or Firebase emulator not running"
            return
        cls.headers = headers

        # Ensure workspace for this user
        ws = ensure_test_workspace(cls.client, cls.headers)
        if not ws:
            cls.skip_tests = True
            cls.skip_reason = "Failed to create or fetch a workspace"
            return
        cls.workspace_id = ws["id"]
        print(f"✅ Using workspace: {cls.workspace_id}")

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

    def test_01_verify_workspace_access(self):
        """Test that we can access the test workspace."""
        print("\n🧪 Step 1: Verifying workspace access")

        # Verify we have a workspace ID
        self.assertIsNotNone(self.workspace_id, "Workspace ID should be set in setUpClass")
        print(f"✅ Using workspace: {self.workspace_id}")

        # Test that we can access workspace actions
        response = self.api_request("GET", f"/workspaces/{self.workspace_id}/actions")
        actions = response.json()
        self.assertIsInstance(actions, list)
        print(f"✅ Workspace has {len(actions)} existing actions")

    def test_02_create_action(self):
        """Test creating an action in the workspace."""
        print("\n🧪 Step 2: Creating action")

        action_data = {
            "name": self.test_action_name,
            "description": "A simple HTTP echo action for testing",
            "type": "REST",
            "config": {
                "url": "https://httpbin.org/anything",
                "method": "POST",
                "headers": {"Content-Type": "application/json", "User-Agent": "ProtoBox-Test/1.0"},
                "timeout": 30,
                "verify_ssl": True,
            },
            "input_schema": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "Message to echo"}},
                "required": ["message"],
            },
            "status": "ACTIVE",
        }

        endpoint = f"/workspaces/{self.workspace_id}/actions"
        response = self.api_request("POST", endpoint, data=action_data, expected_status=201)
        action = response.json()

        # Verify action structure
        self.assertIn("id", action)
        self.assertIn("name", action)
        self.assertEqual(action["name"], self.test_action_name)

        # Store action ID for later tests
        self.action_id = action["id"]
        print(f"✅ Created action: {self.action_id}")

    def test_03_verify_action_available(self):
        """Test that the action is available via MCP tools list."""
        print("\n🧪 Step 3: Verifying action availability")

        # Wait a moment for action to be registered
        time.sleep(2)

        # Create workspace-scoped MCP token and call scoped MCP endpoint
        tr = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/",
            headers=self.headers,
            json={"name": "e2e-openai-token"},
        )
        self.assertEqual(tr.status_code, 200, tr.text)
        mcp_token = tr.json()["token"]
        mcp_headers = {"Authorization": f"Bearer {mcp_token}"}

        # Test MCP tools list endpoint (scoped, non-admin)
        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers=mcp_headers,
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1,
            },
        )
        result = response.json()

        # Verify MCP response structure
        self.assertIn("result", result)
        self.assertIn("tools", result["result"])

        tools = result["result"]["tools"]
        self.assertIsInstance(tools, list)

        # Find our test action
        test_tool = None
        for tool in tools:
            if tool.get("name") == self.test_action_name:
                test_tool = tool
                break

        self.assertIsNotNone(test_tool, f"Action {self.test_action_name} not found in MCP tools")
        print(f"✅ Action available as MCP tool: {test_tool['name']}")

    def test_04_test_mcp_tool_execution(self):
        """Test executing the action via MCP protocol."""
        print("\n🧪 Step 4: Testing MCP tool execution")

        # Create workspace-scoped MCP token and call scoped MCP endpoint
        tr = self.client.post(
            f"/admin/api/v1/workspaces/{self.workspace_id}/mcp-tokens/",
            headers=self.headers,
            json={"name": "e2e-openai-token-call"},
        )
        self.assertEqual(tr.status_code, 200, tr.text)
        mcp_token = tr.json()["token"]
        mcp_headers = {"Authorization": f"Bearer {mcp_token}"}

        response = self.client.post(
            f"/mcp/{self.workspace_id}/tools/call",
            headers=mcp_headers,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": self.test_action_name,
                    "arguments": {"message": "Hello from MCP test!"},
                },
                "id": 2,
            },
        )
        result = response.json()

        # Verify MCP response structure
        self.assertIn("result", result)
        self.assertIn("content", result["result"])

        content = result["result"]["content"]
        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

        # Check for result in content
        content_text = content[0].get("text", "")
        # The REST action is working (status_code: 200), but we need to check for the actual response
        self.assertIn("status_code", content_text)  # Should contain status code
        self.assertIn("200", content_text)  # Should be successful
        print(f"✅ MCP tool execution successful: {content_text[:100]}...")

    def test_05_openai_agents_sdk_integration(self):
        """Test OpenAI Agents SDK integration with MCP server."""
        print("\n🧪 Step 5: Testing OpenAI Agents SDK integration")

        # Skip if OpenAI Agents SDK is not available
        if not OPENAI_AGENTS_AVAILABLE:
            self.skipTest("OpenAI Agents SDK not available - skipping integration test")
            return

        # MCP server URL for this workspace (scoped, non-admin)
        mcp_url = f"http://localhost:8090/mcp/{self.workspace_id}/sse"

        try:
            # Run async test
            asyncio.run(self._test_openai_integration(mcp_url))
        except Exception as e:
            self.fail(f"OpenAI Agents SDK integration failed: {e}")

    async def _test_openai_integration(self, mcp_url):
        """Async helper for OpenAI integration test."""
        # Connect to MCP server via OpenAI Agents SDK
        async with MCPServerSse(name="ProtoBox MCP Test", params={"url": mcp_url}) as mcp_server:
            print("✅ Connected to MCP server via OpenAI Agents SDK")

            # Create agent with MCP tools
            agent = Agent(
                name="MCP Test Agent",
                instructions="You are a helpful assistant with access to ProtoBox actions via MCP. Use the tools when appropriate.",
                mcp_servers=[mcp_server],
            )

            print("✅ Created agent with MCP server connection")

            # Test queries
            test_queries = [
                "What tools do you have available?",
                f"Please use the {self.test_action_name} tool to echo 'Hello from test'",
            ]

            print("\n🤖 Testing OpenAI Agents SDK with MCP tools...")
            print("-" * 50)

            for i, query in enumerate(test_queries, 1):
                print(f"\nTest {i}: {query}")
                print("Response: ", end="")

                result = await Runner.run(starting_agent=agent, input=query)

                print(result.final_output)

                # Verify response contains expected content
                if i == 1:
                    self.assertIn(self.test_action_name, result.final_output.lower())
                elif i == 2:
                    self.assertIn("Hello from test", result.final_output)

            print("\n" + "=" * 50)
            print("🎉 OpenAI Agents SDK integration working!")

    def test_06_cleanup(self):
        """Clean up test resources."""
        print("\n🧪 Step 6: Cleaning up test resources")

        # Delete the action
        if hasattr(self, "action_id"):
            endpoint = f"/workspaces/{self.workspace_id}/actions/{self.action_id}"
            self.api_request("DELETE", endpoint)
            print(f"✅ Deleted action: {self.action_id}")

        # Note: We don't delete the workspace as it might be used by other tests
        # In a real scenario, you might want to clean up the workspace too
        print(f"✅ Test workspace {self.workspace_id} left for other tests")


def run_e2e_test():
    """Run the end-to-end test."""
    print("🚀 Starting E2E MCP OpenAI Integration Test (Fail Fast)")
    print("=" * 60)

    # Check prerequisites
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Using test OpenAI API key for validation")

    # Run synchronous tests first
    print("\n📋 Running synchronous tests...")
    loader = unittest.TestLoader()

    # Create test suite with specific test methods
    suite = unittest.TestSuite()

    # Add specific test methods
    test_class = E2EMCPOpenAITestCase
    suite.addTest(loader.loadTestsFromName("test_01_verify_workspace_access", test_class))
    suite.addTest(loader.loadTestsFromName("test_02_create_action", test_class))
    suite.addTest(loader.loadTestsFromName("test_03_verify_action_available", test_class))
    suite.addTest(loader.loadTestsFromName("test_04_test_mcp_tool_execution", test_class))
    suite.addTest(loader.loadTestsFromName("test_06_cleanup", test_class))

    # Add OpenAI test if available
    if OPENAI_AGENTS_AVAILABLE:
        suite.addTest(loader.loadTestsFromName("test_05_openai_agents_sdk_integration", test_class))
        print("✅ Including OpenAI Agents SDK integration test")
    else:
        print("⚠️ Skipping OpenAI Agents SDK integration test")

    runner = unittest.TextTestRunner(verbosity=2, failfast=True)
    result = runner.run(suite)

    if not result.wasSuccessful():
        print("❌ Tests failed - stopping execution")
        return False

    print("\n" + "=" * 60)
    print("🎉 All E2E tests passed!")
    print("✅ Workspace access: Working")
    print("✅ Action creation: Working")
    print("✅ MCP tool discovery: Working")
    print("✅ MCP tool execution: Working")
    if OPENAI_AGENTS_AVAILABLE:
        print("✅ OpenAI Agents SDK integration: Working")
    else:
        print("⚠️ OpenAI Agents SDK integration: Skipped")

    return True


if __name__ == "__main__":
    success = run_e2e_test()
    sys.exit(0 if success else 1)
