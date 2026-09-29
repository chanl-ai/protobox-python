"""An OAuth authorization code grants an AI client access to one workspace, so it may only
be issued to a member of that workspace. Dynamically registered clients belong to no
workspace until a member picks one at consent."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from protobox.admin.routers import mcp_oauth

WS_A = "64b000000000000000000001"
WS_B = "64b000000000000000000002"
MEMBERSHIPS = {("alice", WS_A)}


class FakeOAuthService:
    def __init__(self, client):
        self.client = client
        self.codes = []
        self.created_clients = []

    async def get_client(self, client_id):
        return self.client

    async def create_authorization_code(self, **kwargs):
        self.codes.append(kwargs)
        return "code-123"

    async def create_client(self, workspace_id, user_id, client_data):
        self.created_clients.append({"workspace_id": workspace_id, "user_id": user_id})
        return SimpleNamespace(client_id="mcp_new", client_name=client_data.client_name,
                               redirect_uris=client_data.redirect_uris)


def make_client(workspace_id):
    return SimpleNamespace(
        client_id="mcp_x", status="active", workspace_id=workspace_id, user_id="owner",
        redirect_uris=["http://localhost:8765/callback"], allowed_scopes=["mcp:read", "mcp:execute"],
    )


@pytest.fixture
def service(monkeypatch):
    holder = {}

    def install(client):
        svc = FakeOAuthService(client)
        monkeypatch.setattr(mcp_oauth, "get_oauth_service", lambda: svc)
        holder["svc"] = svc
        return svc

    async def is_member(workspace_id, user_id):
        return (user_id, workspace_id) in MEMBERSHIPS

    monkeypatch.setattr(mcp_oauth, "_is_workspace_member", is_member)
    return install


async def consent(user_id, workspace_id=None):
    return await mcp_oauth.authorize_consent(
        request=SimpleNamespace(client=None),
        client_id="mcp_x",
        redirect_uri="http://localhost:8765/callback",
        scope="mcp:read",
        code_challenge="challenge",
        code_challenge_method="S256",
        state="s",
        workspace_id=workspace_id,
        user=SimpleNamespace(id=user_id),
    )


@pytest.mark.asyncio
async def test_non_member_cannot_authorize_workspace_client(service):
    svc = service(make_client(WS_A))
    with pytest.raises(HTTPException) as err:
        await consent("mallory")
    assert err.value.status_code == 403
    assert svc.codes == []


@pytest.mark.asyncio
async def test_member_gets_code_for_client_workspace(service):
    svc = service(make_client(WS_A))
    await consent("alice")
    assert svc.codes[0]["workspace_id"] == WS_A


@pytest.mark.asyncio
async def test_workspace_client_cannot_be_redirected_to_another_workspace(service):
    svc = service(make_client(WS_A))
    with pytest.raises(HTTPException) as err:
        await consent("alice", workspace_id=WS_B)
    assert err.value.status_code == 400
    assert svc.codes == []


@pytest.mark.asyncio
async def test_unbound_client_requires_a_workspace_choice(service):
    svc = service(make_client(mcp_oauth.UNBOUND_WORKSPACE))
    with pytest.raises(HTTPException) as err:
        await consent("alice")
    assert err.value.status_code == 400
    assert svc.codes == []


@pytest.mark.asyncio
async def test_unbound_client_rejects_workspace_user_is_not_in(service):
    svc = service(make_client(mcp_oauth.UNBOUND_WORKSPACE))
    with pytest.raises(HTTPException) as err:
        await consent("alice", workspace_id=WS_B)
    assert err.value.status_code == 403
    assert svc.codes == []


@pytest.mark.asyncio
async def test_unbound_client_binds_code_to_chosen_workspace(service):
    svc = service(make_client(mcp_oauth.UNBOUND_WORKSPACE))
    await consent("alice", workspace_id=WS_A)
    assert svc.codes[0]["workspace_id"] == WS_A


@pytest.mark.asyncio
async def test_dynamic_registration_creates_unbound_client(service, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    svc = service(None)
    req = mcp_oauth.DynamicClientRegistrationRequest(
        client_name="Claude", redirect_uris=["http://localhost:8765/callback"])
    await mcp_oauth.dynamic_client_registration(request=SimpleNamespace(), client_req=req)
    assert svc.created_clients == [{"workspace_id": mcp_oauth.UNBOUND_WORKSPACE, "user_id": ""}]
