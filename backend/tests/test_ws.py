import uuid

from fastapi.testclient import TestClient


def test_websocket_session_resumed_and_ping_pong(client: TestClient) -> None:
    session_id = str(uuid.uuid4())
    with client.websocket_connect(f"/ws/{session_id}") as ws:
        # Server sends session_resumed snapshot on connect (FIX ISSUE-20)
        msg = ws.receive_json()
        assert msg["type"] == "session_resumed"
        assert msg["session_id"] == session_id
        assert msg["is_reconnect"] is False
        assert msg["latest_design"] is None
        assert msg["recommendations"] is None
        assert msg["order"] is None

        # ping -> pong
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        assert "timestamp" in pong


def test_websocket_unknown_message_type(client: TestClient) -> None:
    with client.websocket_connect(f"/ws/{uuid.uuid4()}") as ws:
        ws.receive_json()  # session_resumed
        ws.send_json({"type": "text_input", "text": "hello"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["recoverable"] is True
