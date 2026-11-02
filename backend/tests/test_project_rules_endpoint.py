"""Per-project rule sets: presets for the sample, generated rules for uploads."""
import io
import shutil
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routers import workspace as wr
from app.main import app
from app.services.project_fix_proposals import ProjectFixProposalService
from app.services.project_workspace import WorkspaceService

SAMPLE = Path(__file__).resolve().parents[1] / "workspaces" / "orders-api"
PRESET_IDS = {"order-ownership-authorization", "admin-role-authorization", "invoice-ownership-authorization"}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    root = tmp_path / "ws"; root.mkdir()
    shutil.copytree(SAMPLE, root / "orders-api")
    service = WorkspaceService(root)
    monkeypatch.setattr(wr, "workspace_service", service)
    monkeypatch.setattr(wr, "_last_investigations", {})
    monkeypatch.setattr(wr, "fix_proposal_service", ProjectFixProposalService(service))
    return TestClient(app), service


def _open_sample(client):
    r = client.post("/api/workspace/projects", json={"path": "orders-api"})
    assert r.status_code == 200, r.text
    return r.json()


def _zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


def _upload(client, files, name="myproj.zip"):
    r = client.post("/api/workspace/projects/upload", content=_zip_bytes(files),
                    headers={"x-file-name": name, "content-type": "application/zip"})
    assert r.status_code == 200, r.text
    return r.json()


def _rules(client, pid):
    r = client.get(f"/api/workspace/projects/{pid}/rules")
    assert r.status_code == 200, r.text
    return r.json()


def test_sample_gets_presets_and_marker(env):
    client, service = env
    ref = _open_sample(client)
    assert (service.root / ref["relative_path"] / ".forge-project.json").is_file()
    body = _rules(client, ref["project_id"])
    assert body["source"] == "sample" and body["rule_origin"] == "preset"
    assert {r["rule_id"] for r in body["rules"]} == PRESET_IDS and len(body["rules"]) == 3
    assert body["default_rule_id"] == "order-ownership-authorization"


def test_uploaded_sample_folder_gets_generated_only(env):
    client, service = env
    files = {f"orders-api/{p.relative_to(SAMPLE).as_posix()}": p.read_bytes()
             for p in sorted(SAMPLE.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}
    ref = _upload(client, files, name="orders-api.zip")
    body = _rules(client, ref["project_id"])
    assert body["source"] == "upload" and body["rule_origin"] == "generated"
    ids = {r["rule_id"] for r in body["rules"]}
    assert ids and not (ids & PRESET_IDS)
    assert body["default_rule_id"] == body["rules"][0]["rule_id"]


def test_upload_no_routes_empty_rules(env):
    client, service = env
    ref = _upload(client, {"main.py": "def foo():\n    return 1\n"})
    body = _rules(client, ref["project_id"])
    assert body["source"] == "upload" and body["rules"] == [] and body["default_rule_id"] is None


def test_spoofed_marker_in_zip_still_upload(env):
    client, service = env
    ref = _upload(client, {"main.py": "def foo():\n    return 1\n",
                           ".forge-project.json": '{"source": "sample", "sample_path": "orders-api"}'})
    assert not (service.project_root(ref["project_id"]) / ".forge-project.json").exists()
    assert _rules(client, ref["project_id"])["source"] == "upload"


def test_marker_hidden_everywhere(env):
    client, service = env
    ref = _open_sample(client); pid = ref["project_id"]
    assert ".forge-project.json" not in [f["path"] for f in client.get(f"/api/workspace/projects/{pid}/manifest").json()["files"]]
    assert ".forge-project.json" not in [f["path"] for f in client.get(f"/api/workspace/projects/{pid}/files").json()["files"]]
    names = zipfile.ZipFile(io.BytesIO(client.get(f"/api/workspace/projects/{pid}/download").content)).namelist()
    assert ".forge-project.json" not in names
    assert client.get(f"/api/workspace/projects/{pid}/files/content", params={"path": ".forge-project.json"}).status_code == 400


def test_sample_detected_after_restart(env, monkeypatch):
    client, service = env
    ref = _open_sample(client)
    fresh = WorkspaceService(service.root)
    monkeypatch.setattr(wr, "workspace_service", fresh)
    body = _rules(client, ref["project_id"])
    assert body["source"] == "sample" and body["rule_origin"] == "preset"


def test_unknown_project_and_preset_alias(env):
    client, service = env
    assert client.get("/api/workspace/projects/nope/rules").status_code == 404
    r = client.get("/api/workspace/projects/rules")
    assert r.status_code == 200 and {x["rule_id"] for x in r.json()} == PRESET_IDS
