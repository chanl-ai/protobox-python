"""The processor fetches any URL it is given, so it must refuse requests when no API
key is configured instead of running open."""

from fastapi.testclient import TestClient

import main

BODY = {"signed_url": "http://169.254.169.254/latest/meta-data/", "file_type": "pdf"}


def test_unconfigured_key_refuses_requests(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", None)
    response = TestClient(main.app).post("/v1/process", json=BODY)
    assert response.status_code == 503


def test_missing_or_wrong_key_is_rejected(monkeypatch):
    monkeypatch.setattr(main.settings, "api_key", "k" * 40)
    client = TestClient(main.app)
    assert client.post("/v1/process", json=BODY).status_code == 401
    assert client.post("/v1/process", json=BODY, headers={"Authorization": "Bearer nope"}).status_code == 401
