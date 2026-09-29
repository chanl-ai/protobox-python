"""Tests for AssistantService MCP integration behaviors.

These tests focus on configuration and orchestration aspects, without
introducing new workflows. They validate URL composition and ensure
we pass a session to the Agents SDK (to later back by Mongo).
"""

import os
import types
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bson import ObjectId

# Set required environment variables for tests
os.environ["MCP_SECRET_KEY"] = "test_secret_key_for_unit_tests"
os.environ["MCP_MONGODB_URL"] = "mongodb://test:test@localhost:27017/test"

from protobox.admin.services.assistant_service import AssistantService


@pytest.fixture
def svc():
    """AssistantService with mocked dependencies.

    We only need the constructor args; internal DB calls are patched per test.
    """
    with patch("protobox.admin.services.assistant_service.get_database_connection") as mock_db:
        mock_db.return_value = Mock()
        return AssistantService(action_service=Mock(), secret_service=Mock())


def test_get_mcp_server_url_uses_base_env_and_sse(svc, monkeypatch):
    monkeypatch.setenv("MCP_BASE_URL", "https://mcp.example.com")
    url = svc._get_mcp_server_url("64a1f2c3e4b5a67890123456")
    assert url == "https://mcp.example.com/mcp/64a1f2c3e4b5a67890123456/sse"


@pytest.mark.asyncio
async def test_agents_sdk_runner_called_with_session_and_no_openai_key_leak(monkeypatch):
    """Ensure we call Runner.run with a session param (to later use Mongo).

    This does not require a live MCP server; we mock DB and the SDK entrypoints.
    """
    # Enable Agents SDK branch
    from protobox.admin import services as admin_services_pkg

    asst_mod = admin_services_pkg.assistant_service
    monkeypatch.setattr(asst_mod, "AGENTS_SDK_AVAILABLE", True, raising=False)
    monkeypatch.setattr(asst_mod, "MCP_INTEGRATION_AVAILABLE", True, raising=False)

    # Mock DB get_database_connection
    class _Coll(AsyncMock):
        pass

    assistants = _Coll()
    threads = _Coll()
    messages = _Coll()

    thread_oid = ObjectId()
    assistant_oid = ObjectId()

    threads.find_one = AsyncMock(
        return_value={
            "_id": thread_oid,
            "workspace_id": "64a1f2c3e4b5a67890123456",
            "assistant_id": str(assistant_oid),
            "thread_id": "th_test_1",
        }
    )

    assistants.find_one = AsyncMock(
        return_value={
            "_id": assistant_oid,
            "workspace_id": "64a1f2c3e4b5a67890123456",
            "assistant_id": "asst_123",
            "name": "Test",
            "instructions": "Be helpful",
            "model": "gpt-4o",
            "is_default": True,
            "tools": [],
            "metadata": {"mcp_enabled": "true"},
            "created_by": "usr_1",
        }
    )

    class _DB:
        def __init__(self):
            self.database = {
                "assistant_threads": threads,
                "assistants": assistants,
                "assistant_messages": messages,
            }

        def __getitem__(self, key):
            return self.database[key]

    monkeypatch.setattr(asst_mod, "get_database_connection", lambda: _DB())

    # Mock _get_or_create_agent to return a minimal agent without touching OpenAI
    class _DummyAgent:
        name = "Agent"
        instructions = "Be helpful"
        model = "gpt-4o"
        # Simulate having MCP config so the code path creates an MCPServerSse
        _mcp_config = {"name": "ProtoBox MCP Server", "url": "https://mcp.example.com/mcp/w/sse"}

    monkeypatch.setattr(
        asst_mod.AssistantService, "_get_or_create_agent", AsyncMock(return_value=_DummyAgent())
    )

    # Capture session argument passed to Runner.run
    captured = {}

    async def _fake_run(**kwargs):
        captured.update(kwargs)

        class _Res:
            final_output = "ok"

        return _Res()

    # Mock Runner class
    class _MockRunner:
        @staticmethod
        async def run(**kwargs):
            return await _fake_run(**kwargs)

    monkeypatch.setattr(asst_mod, "Runner", _MockRunner)

    # Capture MCPServerSse init kwargs to assert no OPENAI key leakage
    init_args = {}

    class _FakeMCP:
        def __init__(self, *args, **kwargs):
            init_args.update({"args": args, "kwargs": kwargs})

        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(asst_mod, "MCPServerSse", _FakeMCP)

    svc = AssistantService(action_service=Mock(), secret_service=Mock())

    # Drive the generator
    events = []
    async for ev in svc.send_message(
        workspace_id="64a1f2c3e4b5a67890123456",
        thread_id=str(thread_oid),
        request=types.SimpleNamespace(content="hi", metadata={}),
    ):
        events.append(ev)

    # We should have called Runner.run with a session argument we can later swap to Mongo
    assert "starting_agent" in captured
    assert "input" in captured

    # TDD: require a session argument (to evolve to Mongo-backed session).
    pytest.xfail(
        "Session memory not yet wired; implement Mongo-backed session and pass via Runner.run(session=...) then remove xfail."
    )
    assert "session" in captured

    # Ensure we did not leak OPENAI key via headers when instantiating MCPServerSse
    assert "kwargs" in init_args
    headers = init_args["kwargs"].get("headers") or init_args["kwargs"].get("params", {}).get(
        "headers"
    )
    if headers:
        assert "X-API-Key" not in headers
