"""A REST action's decrypted secrets must never reach the logs, and every call to the
egress worker must carry the shared worker token."""

import io
from types import SimpleNamespace

import pytest
from loguru import logger

from protobox.admin.actions.rest_executor import RestActionExecutor

SECRET_VALUE = "sk-live-DO-NOT-LOG-7f3a9c"
JSON_SECRET = '{"api_key": "field-DO-NOT-LOG-91b2", "region": "eu"}'


class FakeSecretService:
    def __init__(self):
        self.secrets = {
            "stripe": SimpleNamespace(id="s1", name="stripe", value=SECRET_VALUE),
            "vendor": SimpleNamespace(id="s2", name="vendor", value=JSON_SECRET),
        }

    async def get_secret_by_name(self, workspace_id, name):
        return self.secrets.get(name)

    async def decrypt_secret_value(self, secret_id, user_id):
        return next(s.value for s in self.secrets.values() if s.id == secret_id)


class FakeResponse:
    status = 200
    content_type = "application/json"
    headers = {}
    reason = "OK"

    async def json(self):
        return {"status_code": 200, "body": {"ok": True}}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class RecordingSession:
    def __init__(self):
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return FakeResponse()


@pytest.fixture
def captured_logs():
    sink = io.StringIO()
    handler_id = logger.add(sink, level="TRACE", format="{message}")
    yield sink
    logger.remove(handler_id)


@pytest.fixture
def executor(monkeypatch):
    async def no_refresh(secret, value, workspace_id, user_id):
        return value

    ex = RestActionExecutor(FakeSecretService())
    monkeypatch.setattr(ex, "_refresh_oauth_token_if_needed", no_refresh)
    return ex


def request_config():
    return {
        "url": "https://api.example.com/charge",
        "method": "POST",
        "headers": {
            "Authorization": "Bearer ${secret:stripe}",
            "X-Vendor-Key": "${secret:vendor.api_key}",
        },
        "json": {"amount": 100},
        "timeout": 5,
        "allow_redirects": True,
        "verify_ssl": True,
    }


@pytest.mark.asyncio
async def test_secret_values_are_not_logged(executor, captured_logs, monkeypatch):
    monkeypatch.setenv("REST_EXECUTOR_WORKER_URL", "https://egress.internal/run")
    monkeypatch.setenv("REST_EXECUTOR_WORKER_TOKEN", "worker-token-DO-NOT-LOG")
    config = request_config()

    await executor._process_secrets(config, "ws1", "u1")
    await executor._make_request(RecordingSession(), config)

    # The substitution itself must still work.
    assert config["headers"]["Authorization"] == f"Bearer {SECRET_VALUE}"
    assert config["headers"]["X-Vendor-Key"] == "field-DO-NOT-LOG-91b2"

    logs = captured_logs.getvalue()
    assert logs, "expected the executor to log something; the sink is not attached"
    for leaked in (SECRET_VALUE, "field-DO-NOT-LOG-91b2", "worker-token-DO-NOT-LOG"):
        assert leaked not in logs


@pytest.mark.asyncio
async def test_worker_call_carries_worker_token(executor, monkeypatch):
    monkeypatch.setenv("REST_EXECUTOR_WORKER_URL", "https://egress.internal/run")
    monkeypatch.setenv("REST_EXECUTOR_WORKER_TOKEN", "worker-token-abc")
    session = RecordingSession()

    await executor._make_request(session, request_config())

    assert session.calls[0]["headers"]["Authorization"] == "Bearer worker-token-abc"


@pytest.mark.asyncio
async def test_worker_call_refused_without_token(executor, monkeypatch):
    monkeypatch.setenv("REST_EXECUTOR_WORKER_URL", "https://egress.internal/run")
    monkeypatch.delenv("REST_EXECUTOR_WORKER_TOKEN", raising=False)

    with pytest.raises(ValueError, match="REST_EXECUTOR_WORKER_TOKEN"):
        await executor._make_request(RecordingSession(), request_config())
