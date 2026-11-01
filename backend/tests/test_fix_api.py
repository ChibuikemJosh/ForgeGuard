"""API tests for the fix endpoint contract."""

from fastapi.testclient import TestClient

import app.services.fix as fix_service
from app.main import app
from app.schemas.fix import FixResult

client = TestClient(app)


def test_fix_returns_agent_fixes(monkeypatch, tmp_path) -> None:
    target = tmp_path / "orders.py"
    target.write_text("x = 1\n", encoding="utf-8")

    def fake_fix(customviolation: str, filenames: list[str]):
        assert customviolation == "Order of another customer being passed through"
        assert filenames == [str(target)]
        return [FixResult(filename=str(target), fixedCode="x = 2\n")]

    monkeypatch.setattr(fix_service._agent, "fix_violations", fake_fix)
    response = client.post(
        "/fix",
        json={
            "filenames": [str(target)],
            "customviolation": "Order of another customer being passed through",
        },
    )

    assert response.status_code == 200
    assert response.json() == [{"filename": str(target), "fixedCode": "x = 2\n"}]


def test_fix_rejects_missing_fields() -> None:
    response = client.post("/fix", json={"filenames": []})

    assert response.status_code == 422


def test_fix_reports_missing_api_key(monkeypatch, tmp_path) -> None:
    target = tmp_path / "orders.py"
    target.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setenv("META_MODEL_API_KEY", "")
    response = client.post(
        "/fix",
        json={"filenames": [str(target)], "customviolation": "anything"},
    )

    assert response.status_code == 503
    assert "META_MODEL_API_KEY" in response.json()["detail"]


def test_fix_rejects_unknown_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    response = client.post(
        "/fix",
        json={
            "filenames": [str(tmp_path / "missing.py")],
            "customviolation": "anything",
        },
    )

    assert response.status_code == 400
