"""Tests for Project Investigation endpoints (sample, files, rules, fixes, upload)."""
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routers import workspace as wr
from app.main import app
from app.schemas.chat import ChatLocation
from app.services.project_fix_proposals import ProjectFixProposalService
from app.services.project_workspace import WorkspaceService
from app.services.security_investigation import SecurityInvestigationService

SAMPLE = Path(__file__).resolve().parents[1] / "workspaces" / "orders-api"


class FakeAgent:
    last_truncated = False

    def __init__(self, locations, truncated=False):
        self.locations = locations
        self.last_truncated = truncated

    def find_violations(self, details, folder, session_id):
        return self.locations


@pytest.fixture()
def client_env(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    root.mkdir()
    # copy sample into tmp workspace
    import shutil
    shutil.copytree(SAMPLE, root / "orders-api")
    service = WorkspaceService(root)
    monkeypatch.setattr(wr, "workspace_service", service)
    monkeypatch.setattr(wr, "_last_investigations", {})
    fix = ProjectFixProposalService(service)
    monkeypatch.setattr(wr, "fix_proposal_service", fix)
    return TestClient(app), service, fix


def _open(client):
    r = client.post("/api/workspace/projects", json={"path": "orders-api"})
    assert r.status_code == 200, r.text
    return r.json()["project_id"]


def _rel(client, pid):
    return client.get(f"/api/workspace/projects/{pid}").json()["relative_path"]


def test_samples_and_register(client_env):
    client, _, _ = client_env
    r = client.get("/api/workspace/samples")
    assert r.status_code == 200
    assert r.json()[0]["path"] == "orders-api"
    pid = _open(client)
    m = client.get(f"/api/workspace/projects/{pid}/manifest").json()
    assert m["python_file_count"] >= 7


def test_file_content_ok_unknown_traversal_sensitive(client_env):
    client, _, _ = client_env
    pid = _open(client)
    ok = client.get(f"/api/workspace/projects/{pid}/files/content", params={"path": "routes/orders.py"})
    assert ok.status_code == 200 and "get_order" in ok.json()["content"] and ok.json()["sha256"]
    assert client.get(f"/api/workspace/projects/{pid}/files/content", params={"path": "nope.py"}).status_code == 404
    assert client.get(f"/api/workspace/projects/{pid}/files/content", params={"path": "../secret.py"}).status_code == 400
    assert client.get(f"/api/workspace/projects/{pid}/files/content", params={"path": ".env"}).status_code == 400
    assert client.get("/api/workspace/projects/project-nope/files/content", params={"path": "main.py"}).status_code == 404


def test_rules_list(client_env):
    client, _, _ = client_env
    rules = client.get("/api/security/rules").json()
    ids = {r["rule_id"] for r in rules}
    assert "order-ownership-authorization" in ids and "admin-role-authorization" in ids
    assert client.get("/api/workspace/rules").json()[0]["rule_id"]


def test_custom_rule_is_forwarded_to_investigator(client_env, monkeypatch):
    client, service, _ = client_env
    pid = _open(client)
    captured = {}

    class RuleAgent:
        last_truncated = False

        def find_violations(self, details, folder, session_id):
            captured["details"] = details
            return []

    monkeypatch.setattr(
        wr,
        "_investigator",
        SecurityInvestigationService(service, agent=RuleAgent()),
    )
    rule = {
        "rule_id": "transfer-limit",
        "title": "Daily transfer limit",
        "invariant": "A customer's daily money transfers must not exceed $2,000.",
    }
    response = client.post(
        f"/api/workspace/projects/{pid}/investigate",
        json={"rule": rule},
    )
    assert response.status_code == 200
    assert "$2,000" in captured["details"]


def test_invalid_rule_is_rejected(client_env):
    client, _, _ = client_env
    pid = _open(client)
    response = client.post(
        f"/api/workspace/projects/{pid}/investigate",
        json={"rule": {"rule_id": "   "}},
    )
    assert response.status_code == 422


def test_non_python_upload_is_rejected(client_env):
    client, _, _ = client_env
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("README.md", "# JavaScript project\n")
    response = client.post(
        "/api/workspace/projects/upload",
        content=buffer.getvalue(),
        headers={"content-type": "application/zip", "x-file-name": "frontend.zip"},
    )
    assert response.status_code == 422
    assert "no Python files" in response.json()["detail"]


def test_source_graph_has_routes(client_env):
    client, _, _ = client_env
    pid = _open(client)
    graph = client.get(f"/api/workspace/projects/{pid}/source-graph").json()
    assert graph["summary"]["routes"] >= 4
    labels = {n["name"] for n in graph["nodes"] if n["type"] == "route"}
    assert labels  # route nodes exist


def test_investigate_stubbed_and_truncation(client_env, monkeypatch):
    client, service, _fix = client_env
    pid = _open(client)
    agent = FakeAgent([ChatLocation(filename="routes/orders.py", linenumber=12)], truncated=True)
    monkeypatch.setattr(wr, "_investigator", SecurityInvestigationService(service, agent=agent))
    r = client.post(f"/api/workspace/projects/{pid}/investigate", json={"rule": {"rule_id": "order-ownership-authorization", "title": "T", "invariant": "I"}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["findings"][0]["status"] == "potential"
    assert body["findings"][0]["evidence"][0]["status"] == "valid"
    assert body["findings"][0]["related_graph_nodes"]
    assert any("truncated" in e for e in body["errors"])


def _setup_finding(client_env, monkeypatch, proposed=None):
    client, service, fix = client_env
    pid = _open(client)
    agent = FakeAgent([ChatLocation(filename="routes/orders.py", linenumber=12)])
    monkeypatch.setattr(wr, "_investigator", SecurityInvestigationService(service, agent=agent))
    body = client.post(f"/api/workspace/projects/{pid}/investigate", json={"rule": {"rule_id": "r", "title": "T", "invariant": "I"}}).json()
    finding_id = body["findings"][0]["finding_id"]
    original = (Path(service.root) / _rel(client, pid) / "routes/orders.py").read_text()
    fixed = proposed if proposed is not None else original.replace("    return order\n", "    if order.owner_id != customer.customer_id:\n        raise HTTPException(status_code=403, detail='no')\n    return order\n")
    fix.generator = lambda *a, **k: {"file_path": "routes/orders.py", "proposed_content": fixed, "explanation": "check owner"}
    return client, service, fix, pid, finding_id, original


def test_fix_lifecycle(client_env, monkeypatch):
    client, service, fix, pid, finding_id, original = _setup_finding(client_env, monkeypatch)
    r = client.post(f"/api/workspace/projects/{pid}/findings/{finding_id}/fix-proposals", json={"instructions": "fix it"})
    assert r.status_code == 200, r.text
    prop = r.json()
    assert prop["review_status"] == "pending" and prop["unified_diff"]
    target = Path(service.root) / _rel(client, pid) / "routes/orders.py"
    assert target.read_text() == original  # never auto-applied
    # AI actor rejected
    bad = client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/review", json={"decision": "approved", "reviewer": "x", "actor": "ai"})
    assert bad.status_code == 409
    # apply before approval -> 409
    assert client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/apply").status_code == 409
    ok = client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/review", json={"decision": "approved", "reviewer": "kenny", "actor": "human"})
    assert ok.status_code == 200 and ok.json()["review_status"] == "approved"
    applied = client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/apply")
    assert applied.status_code == 200 and applied.json()["application_status"] == "applied"
    assert "owner_id" in target.read_text()
    rolled = client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/rollback")
    assert rolled.status_code == 200 and target.read_text() == original


def test_fix_hash_mismatch_409(client_env, monkeypatch):
    client, service, fix, pid, finding_id, original = _setup_finding(client_env, monkeypatch)
    prop = client.post(f"/api/workspace/projects/{pid}/findings/{finding_id}/fix-proposals", json={}).json()
    client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/review", json={"decision": "approved", "reviewer": "k", "actor": "human"})
    target = Path(service.root) / _rel(client, pid) / "routes/orders.py"
    target.write_text(original + "\n# changed\n")
    assert client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/apply").status_code == 409


def test_fix_invalid_python_502(client_env, monkeypatch):
    client, service, fix, pid, finding_id, original = _setup_finding(client_env, monkeypatch, proposed="def broken(:\n")
    r = client.post(f"/api/workspace/projects/{pid}/findings/{finding_id}/fix-proposals", json={})
    assert r.status_code == 502


def test_fix_invalid_python_is_logged(client_env, monkeypatch, caplog):
    client, service, fix, pid, finding_id, original = _setup_finding(client_env, monkeypatch, proposed="def broken(:\n")
    with caplog.at_level("WARNING", logger="app.services.project_fix_proposals"):
        client.post(f"/api/workspace/projects/{pid}/findings/{finding_id}/fix-proposals", json={})
    assert any("Fix proposal rejected" in r.message and "not valid Python" in r.message for r in caplog.records)


@pytest.mark.parametrize("returned_path", ["orders-api/routes/orders.py", "./routes/orders.py", "/routes/orders.py", "other.py"])
def test_fix_uses_backend_path_not_model_path(client_env, monkeypatch, returned_path):
    client, service, fix, pid, finding_id, original = _setup_finding(client_env, monkeypatch)
    inner = fix.generator
    fix.generator = lambda *a, **k: {**inner(*a, **k), "file_path": returned_path}
    r = client.post(f"/api/workspace/projects/{pid}/findings/{finding_id}/fix-proposals", json={})
    assert r.status_code == 200, r.text
    assert r.json()["file_path"] == "routes/orders.py"


def test_parse_json_object_tolerates_surrounding_text():
    from app.services.project_fix_proposals import _parse_json_object

    assert _parse_json_object('Here is the fix:\n{"file_path": "a.py", "proposed_content": "x = 1\\n"}\nDone.')["file_path"] == "a.py"
    assert _parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert _parse_json_object("no json here") is None


def test_fix_unknown_finding_404(client_env, monkeypatch):
    client, service, fix, pid, finding_id, original = _setup_finding(client_env, monkeypatch)
    assert client.post(f"/api/workspace/projects/{pid}/findings/nope/fix-proposals", json={}).status_code == 404


def test_upload_zip_then_investigate(client_env, monkeypatch):
    client, service, fix = client_env
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("proj/main.py", "def foo():\n    return 1\n")
        z.writestr("../evil.py", "x=1\n")
        z.writestr(".env", "SECRET=1\n")
    # traversal entry should be rejected
    bad = client.post("/api/workspace/projects/upload", content=buf.getvalue(), headers={"x-file-name": "proj.zip", "content-type": "application/zip"})
    assert bad.status_code == 400
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as z:
        z.writestr("main.py", "def foo():\n    return 1\n")
        z.writestr(".env", "SECRET=1\n")
    r = client.post("/api/workspace/projects/upload", content=buf2.getvalue(), headers={"x-file-name": "myproj.zip", "content-type": "application/zip"})
    assert r.status_code == 200, r.text
    pid = r.json()["project_id"]
    m = client.get(f"/api/workspace/projects/{pid}/manifest").json()
    assert [f["path"] for f in m["files"]] == ["main.py"]  # .env excluded
    agent = FakeAgent([ChatLocation(filename="main.py", linenumber=1)])
    monkeypatch.setattr(wr, "_investigator", SecurityInvestigationService(service, agent=agent))
    # uploaded project registered on same service; investigator uses that service
    inv = client.post(f"/api/workspace/projects/{pid}/investigate", json={"rule": {"rule_id": "r", "title": "T", "invariant": "I"}})
    assert inv.status_code == 200 and inv.json()["findings"][0]["status"] == "potential"


def _zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


def _upload(client, files, name="myproj.zip"):
    return client.post("/api/workspace/projects/upload", content=_zip_bytes(files),
                       headers={"x-file-name": name, "content-type": "application/zip"})


def test_recovery_after_restart(client_env):
    client, service, _ = client_env
    r = _upload(client, {"app.py": "def foo():\n    return 1\n"})
    assert r.status_code == 200, r.text
    pid = r.json()["project_id"]
    fresh = WorkspaceService(service.root)  # simulate restart: empty registry
    assert fresh.get_project(pid).project_id == pid
    assert fresh.project_root(pid).is_dir()
    from app.services.project_workspace import WorkspaceError
    with pytest.raises(WorkspaceError):
        fresh.get_project("project-000000000000")


def test_upload_syntax_error_graph_still_200(client_env):
    client, _, _ = client_env
    r = _upload(client, {"good.py": "def ok():\n    return 1\n", "bad.py": 'print "x"\n'}, "mixed.zip")
    assert r.status_code == 200, r.text
    pid = r.json()["project_id"]
    graph = client.get(f"/api/workspace/projects/{pid}/source-graph")
    assert graph.status_code == 200
    assert any(n.get("file_path") == "good.py" or n.get("name") == "ok" for n in graph.json()["nodes"])


def test_upload_ds_store_skipped(client_env):
    client, _, _ = client_env
    r = _upload(client, {"myproj/app.py": "x = 1\n", "myproj/.DS_Store": "junk"}, "ds.zip")
    assert r.status_code == 200, r.text
    pid = r.json()["project_id"]
    m = client.get(f"/api/workspace/projects/{pid}/manifest").json()
    paths = [f["path"] for f in m["files"]]
    assert "app.py" in paths and not any(".DS_Store" in p for p in paths)


def test_upload_ttl_cleanup(client_env, monkeypatch):
    client, service, _ = client_env
    import os as _os, time as _time
    old = service.root / "oldproj-deadbeef"
    old.mkdir(); (old / "a.py").write_text("x=1\n")
    past = _time.time() - 10 * 3600
    _os.utime(old, (past, past))
    r = _upload(client, {"app.py": "x = 1\n"}, "newproj.zip")
    assert r.status_code == 200, r.text
    assert not old.exists()
    assert (service.root / "orders-api").is_dir()


def test_open_project_forbidden_in_production(client_env, monkeypatch):
    client, _, _ = client_env
    monkeypatch.setenv("FORGE_ENV", "production")
    assert client.post("/api/workspace/projects", json={"path": "."}).status_code == 403
    assert client.post("/api/workspace/projects", json={"path": "orders-api"}).status_code == 200


def test_security_apply_disabled_in_production(client_env, monkeypatch):
    client, _, _ = client_env
    monkeypatch.setenv("FORGE_ENV", "production")
    assert client.post("/api/security/proposals/whatever/apply").status_code == 403
    assert client.post("/api/security/proposals/whatever/rollback").status_code == 403


def test_collect_python_files_prioritises_relevant(tmp_path):
    from app.services.violations_finder_agent import _collect_python_files
    (tmp_path / "zzz_util.py").write_text("x=1\n")
    (tmp_path / "aaa_misc.py").write_text("x=1\n")
    sub = tmp_path / "routes"; sub.mkdir(); (sub / "orders.py").write_text("x=1\n")
    files, _ = _collect_python_files(tmp_path)
    assert files[0][0] == "routes/orders.py"
