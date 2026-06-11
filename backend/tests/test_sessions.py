import uuid

from fastapi.testclient import TestClient


def test_create_session_stub(client: TestClient) -> None:
    resp = client.post("/api/v1/sessions")
    assert resp.status_code == 201
    body = resp.json()
    # Contract: session_id, state, created_at, ws_path (api_contracts.md)
    session_id = body["session_id"]
    uuid.UUID(session_id)  # valid UUID
    assert body["state"] == "greeting"
    assert body["ws_path"] == f"/ws/{session_id}"
    assert "created_at" in body


def test_get_session_not_implemented(client: TestClient) -> None:
    resp = client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert resp.status_code == 501
