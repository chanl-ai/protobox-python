"""Test Knowledge Base MCP Integration."""

import asyncio

import pytest

from .test_complete_user_flow import PYTHON_API_URL, E2ETestHelper


@pytest.mark.asyncio
async def test_kb_search_tool_in_mcp_tools():
    """Test that KB search tool is included in MCP tools list and can be executed."""
    async with E2ETestHelper() as helper:
        # Step 1: Authenticate
        await helper.sign_in_firebase_user()
        await helper.exchange_firebase_token()

        # Use test workspace
        helper.workspace_id = "6883c972274b0349b71b5ff2"

        # Step 2: List MCP tools
        async with helper.session.post(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/mcp/tools/list",
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1},
            headers=helper.cookies,
        ) as resp:
            assert resp.status == 200
            data = await resp.json()

            # Check response structure
            assert "jsonrpc" in data
            assert data["jsonrpc"] == "2.0"
            assert "result" in data
            assert "tools" in data["result"]

            # Find KB search tool
            tools = data["result"]["tools"]
            kb_tool = next(
                (tool for tool in tools if tool["name"] == "search_knowledge_base"), None
            )

            assert kb_tool is not None, "KB search tool not found in MCP tools list"
            assert (
                kb_tool["description"]
                == "Search the workspace knowledge base for relevant information to help answer questions"
            )

            print("✅ Found KB search tool in MCP tools list")

        # Step 3: Create a KB entry for testing
        entry_data = {
            "title": "MCP Test Entry",
            "category": "testing",
            "tags": ["mcp", "test"],
            "qna_pairs": [
                {
                    "question": "What is MCP testing?",
                    "answer": "MCP testing ensures Model Context Protocol integration works correctly with Knowledge Base search.",
                    "keywords": ["mcp", "testing", "integration"],
                }
            ],
        }

        async with helper.session.post(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/knowledge/entries",
            json=entry_data,
            headers=helper.cookies,
        ) as resp:
            assert resp.status == 201
            print("✅ Created KB entry for testing")

        # Wait for indexing
        await asyncio.sleep(0.5)

        # Step 4: Call KB search via MCP
        async with helper.session.post(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/mcp/tools/call",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search_knowledge_base",
                    "arguments": {
                        "query": "MCP testing",
                        "max_results": 3,
                        "search_type": "semantic",
                    },
                },
                "id": 2,
            },
            headers=helper.cookies,
        ) as resp:
            assert resp.status == 200
            data = await resp.json()

            # Check response
            assert "result" in data
            content = data["result"]["content"][0]
            assert content["type"] == "text"

            # Should contain our entry
            assert "MCP Test Entry" in content["text"]
            assert "What is MCP testing?" in content["text"]
            print("✅ KB search via MCP returned expected results")

        # Step 5: Test error handling
        async with helper.session.post(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/mcp/tools/call",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "search_knowledge_base", "arguments": {}},  # Missing query
                "id": 3,
            },
            headers=helper.cookies,
        ) as resp:
            assert resp.status == 400
            data = await resp.json()
            assert "error" in data
            assert "Missing required parameter: query" in data["error"]["message"]
            print("✅ KB search error handling works correctly")


@pytest.mark.asyncio
async def test_kb_tool_with_assistant():
    """Test that assistants can use the KB search tool."""
    async with E2ETestHelper() as helper:
        # Step 1: Authenticate
        await helper.sign_in_firebase_user()
        await helper.exchange_firebase_token()

        # Use test workspace
        helper.workspace_id = "6883c972274b0349b71b5ff2"

        # Step 2: Create or use existing assistant
        # Note: This test verifies the KB tool is available but doesn't test
        # the OpenAI Agents SDK integration since that requires additional setup

        # List assistants to find KB Test Assistant
        async with helper.session.get(
            f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/assistants", headers=helper.cookies
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                assistants = data.get("assistants", [])
                kb_assistant = next(
                    (a for a in assistants if a["name"] == "KB Test Assistant"), None
                )

                if kb_assistant:
                    print(
                        f"✅ Found KB Test Assistant with MCP enabled: {kb_assistant.get('mcp_enabled')}"
                    )
                    assert kb_assistant.get("mcp_enabled") == True
                else:
                    print("⚠️ KB Test Assistant not found")

        # Step 3: Verify MCP endpoint is accessible
        # This would be used by the assistant when OpenAI Agents SDK is working
        mcp_info_url = f"{PYTHON_API_URL}/workspaces/{helper.workspace_id}/mcp/"
        async with helper.session.get(mcp_info_url, headers=helper.cookies) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ MCP endpoint info retrieved: {data.get('server_name')}")
                assert data.get("capabilities", {}).get("tools") == True

                # Check SSE endpoint is listed
                sse_endpoint = data.get("endpoints", {}).get("sse")
                assert sse_endpoint is not None
                assert f"workspaces/{helper.workspace_id}/mcp/sse" in sse_endpoint
