"""Integration tests validating MCP JSON-RPC contract per OpenAI MCP docs.

This focuses on POST tools/list and tools/call endpoints exposed at
`/mcp/{workspace_id}/...` using Bearer auth with an MCP token created via
the admin API. We assert JSON-RPC 2.0 shapes as described in the docs:
https://platform.openai.com/docs/mcp
"""

import pytest
from bson import ObjectId
from httpx import Client

from .test_utils import get_emulator_auth_token


@pytest.mark.integration
class TestMcpDocsContract:
    @classmethod
    def setup_class(cls):
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        cls.skip = False
        try:
            cls.client.get("/admin/api/v1/health")
        except Exception as e:
            cls.skip = True
            cls.skip_reason = f"Server not running: {e}"
            return

        # Auth for admin API
        cls.token, cls.refresh_token, cls.headers = get_emulator_auth_token(cls.client)
        if not cls.token:
            cls.skip = True
            cls.skip_reason = "Authentication not enabled or Firebase emulator not running"
            return

        # Workspace
        ws_resp = cls.client.get("/admin/api/v1/workspaces", headers=cls.headers)
        if ws_resp.status_code != 200:
            cls.skip = True
            cls.skip_reason = "Failed to list workspaces"
            return
        workspaces = ws_resp.json().get("workspaces", [])
        if workspaces:
            cls.workspace_id = workspaces[0]["id"]
        else:
            slug = f"mcp-docs-{ObjectId()}"
            cr = cls.client.post(
                "/admin/api/v1/workspaces",
                headers=cls.headers,
                json={"name": "MCP Docs Test", "slug": slug},
            )
            assert cr.status_code in (200, 201)
            cls.workspace_id = cr.json()["id"]

        # Create an MCP token for Bearer auth
        tr = cls.client.post(
            f"/admin/api/v1/workspaces/{cls.workspace_id}/mcp-tokens/",
            headers=cls.headers,
            json={"name": "mcp-docs-token"},
        )
        assert tr.status_code == 200, tr.text
        tdata = tr.json()
        cls.mcp_token = tdata["token"]
        # Convenience auth header for MCP endpoints
        cls.mcp_headers = {"Authorization": f"Bearer {cls.mcp_token}"}

    def setup_method(self):
        if getattr(self, "skip", False):
            pytest.skip(getattr(self, "skip_reason", "Skipping MCP docs contract tests"))

    def test_tools_list_jsonrpc_contract(self):
        r = self.client.post(
            f"/mcp/{self.workspace_id}/tools/list",
            headers=self.mcp_headers,
            json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1},
        )
        assert r.status_code == 200
        data = r.json()
        # JSON-RPC 2.0 top-level
        assert data.get("jsonrpc") == "2.0"
        assert "result" in data and isinstance(data["result"], dict)
        tools = data["result"].get("tools")
        assert isinstance(tools, list)
        # If tools exist, validate minimal schema
        if tools:
            tool = tools[0]
            assert "name" in tool
            assert "inputSchema" in tool and isinstance(tool["inputSchema"], dict)

    def test_tools_call_error_shape_for_unknown_tool(self):
        r = self.client.post(
            f"/mcp/{self.workspace_id}/tools/call",
            headers=self.mcp_headers,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
                "id": 2,
            },
        )
        # Expect 404 for missing tool, with JSON-RPC error body
        assert r.status_code in (400, 404)
        data = r.json()
        assert data.get("jsonrpc") == "2.0"
        assert "error" in data and isinstance(data["error"], dict)
        assert "message" in data["error"]
