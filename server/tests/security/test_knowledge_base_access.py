"""Knowledge base routes must require a signed-in member of the workspace, and a
processing task is only visible from the workspace that owns it. Driven through the
real router so an unattached dependency shows up as a failure."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from protobox.admin.auth.dependencies import get_current_user
from protobox.admin.routers import knowledge_base
from protobox.admin.routers.audit import get_audit_service
from protobox.admin.routers.workspace import verify_workspace_access

WS = "64b000000000000000000001"
OTHER_WS = "64b000000000000000000002"
DOC = "64b0000000000000000000aa"


class FakeKbService:
    def __init__(self):
        self.calls = []

    async def list_documents(self, **kwargs):
        self.calls.append("list")
        return []

    async def get_document(self, workspace_id, document_id):
        self.calls.append("get")
        return None

    async def get_task_status(self, task_id):
        self.calls.append("task")
        return {"_id": task_id, "workspace_id": OTHER_WS, "status": "completed"}

    async def delete_document(self, *args, **kwargs):
        self.calls.append("delete")
        return True


@pytest.fixture
def app_and_service():
    app = FastAPI()
    app.include_router(knowledge_base.router)
    svc = FakeKbService()
    app.dependency_overrides[knowledge_base.get_knowledge_document_service] = lambda: svc
    app.dependency_overrides[get_audit_service] = lambda: SimpleNamespace()
    return app, svc


READ_ROUTES = [
    ("GET", f"/workspaces/{WS}/knowledge"),
    ("GET", f"/workspaces/{WS}/knowledge/{DOC}"),
    ("GET", f"/workspaces/{WS}/knowledge/tasks/task-1"),
    ("DELETE", f"/workspaces/{WS}/knowledge/{DOC}"),
]


@pytest.mark.parametrize("method,path", READ_ROUTES)
def test_anonymous_request_is_rejected(app_and_service, method, path):
    app, svc = app_and_service
    app.dependency_overrides[get_current_user] = lambda: None
    response = TestClient(app).request(method, path)
    assert response.status_code == 401
    assert svc.calls == []


@pytest.mark.parametrize("method,path", READ_ROUTES)
def test_non_member_is_rejected(app_and_service, method, path):
    app, svc = app_and_service
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="mallory")

    def deny():
        raise HTTPException(status_code=403, detail="Access denied")

    app.dependency_overrides[verify_workspace_access] = deny
    response = TestClient(app).request(method, path)
    assert response.status_code == 403
    assert svc.calls == []


def test_task_from_another_workspace_is_not_found(app_and_service):
    app, svc = app_and_service
    app.dependency_overrides[verify_workspace_access] = lambda: ("alice", WS)
    response = TestClient(app).get(f"/workspaces/{WS}/knowledge/tasks/task-1")
    assert response.status_code == 404
