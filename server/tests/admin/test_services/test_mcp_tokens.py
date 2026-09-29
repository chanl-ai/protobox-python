"""Tests for MCP token router responses and URL.

Keeps existing workflow (pytest). These tests validate we return a usable
`mcp_url` with `/sse` and never expose token secrets when listing.
"""

import os
import types
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

# Set required environment variables for tests
os.environ["MCP_SECRET_KEY"] = "test_secret_key_for_unit_tests"
os.environ["MCP_MONGODB_URL"] = "mongodb://test:test@localhost:27017/test"

from protobox.admin.routers import mcp_tokens as router_mod


@pytest.mark.asyncio
async def test_create_returns_url_with_sse(monkeypatch):
    async def _create_mcp_token(db, workspace_id, name, description, expires_in_days, scopes):
        return {
            "token": "plain-once",
            "token_id": "tok_1",
            "name": name,
            "workspace_id": workspace_id,
            "mcp_url": f"https://mcp.example.com/mcp/{workspace_id}/sse",
            "expires_at": datetime.utcnow() + timedelta(days=1),
        }

    class _DB:
        def __init__(self):
            self.database = {"audit_logs": AsyncMock()}

    monkeypatch.setattr(router_mod, "get_database_connection", lambda: _DB())
    monkeypatch.setattr(
        router_mod.MCPAuthService, "create_mcp_token", AsyncMock(side_effect=_create_mcp_token)
    )

    resp = await router_mod.create_mcp_token(
        workspace_id="64a1f2c3e4b5a67890123456",
        request=router_mod.CreateMCPTokenRequest(name="Test"),
        current_user=Mock(user_id="u1"),
    )

    assert resp.mcp_url.endswith("/sse")
    assert resp.token == "plain-once"


@pytest.mark.asyncio
async def test_list_does_not_expose_plain_tokens(monkeypatch):
    class _DB:
        def __init__(self):
            self.database = {"mcp_tokens": AsyncMock()}

    tokens = [
        {
            "token_id": "tok_1",
            "name": "t1",
            "workspace_id": "64a1f2c3e4b5a67890123456",  # Valid MongoDB ObjectId
            "scopes": ["default"],
            "created_at": datetime.utcnow(),
            "status": "active",
            "usage_count": 0,
        }
    ]

    db = _DB()
    db.database["mcp_tokens"].find = Mock(
        return_value=types.SimpleNamespace(to_list=AsyncMock(return_value=tokens))
    )

    monkeypatch.setattr(router_mod, "get_database_connection", lambda: db)

    res = await router_mod.list_mcp_tokens(
        workspace_id="64a1f2c3e4b5a67890123456",  # Valid MongoDB ObjectId
        current_user=Mock(user_id="u1"),
        include_revoked=False,
    )
    assert len(res) == 1
    # No `token` field present in response model
    assert not hasattr(res[0], "token")
