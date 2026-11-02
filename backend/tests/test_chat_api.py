"""API tests for the chat endpoint contract."""

from fastapi.testclient import TestClient

import app.services.chat as chat_service
from app.main import app
from app.schemas.chat import ChatLocation

client = TestClient(app)


def test_chat_returns_agent_locations(monkeypatch, tmp_path) -> None:
    def fake_find(details: str, project_folder: str, session_id: str):
        assert details == "unsanitized query in login handler"
        assert project_folder == str(tmp_path)
        assert session_id == "session-123"
        return [ChatLocation(filename="app/views.py", linenumber=42)]

    monkeypatch.setattr(chat_service._agent, "find_violations", fake_find)
    response = client.post(
        "/chat",
        json={
            "custom_security_violation_details": "unsanitized query in login handler",
            "project_folder": str(tmp_path),
            "session_id": "session-123",
        },
    )

    assert response.status_code == 200
    assert response.json() == [{"filename": "app/views.py", "linenumber": 42, "relatednodes": []}]


def test_chat_rejects_missing_fields() -> None:
    response = client.post("/chat", json={"session_id": "session-123"})

    assert response.status_code == 422


def test_chat_reports_missing_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("META_MODEL_API_KEY", "")
    response = client.post(
        "/chat",
        json={
            "custom_security_violation_details": "anything",
            "project_folder": str(tmp_path),
            "session_id": "session-123",
        },
    )

    assert response.status_code == 503
    assert "META_MODEL_API_KEY" in response.json()["detail"]


def test_chat_rejects_unknown_project_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    response = client.post(
        "/chat",
        json={
            "custom_security_violation_details": "anything",
            "project_folder": str(tmp_path / "missing"),
            "session_id": "session-123",
        },
    )

    assert response.status_code == 400
