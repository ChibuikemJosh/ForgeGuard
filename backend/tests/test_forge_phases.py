"""Tests for Phases 1-4: sample copies, downloads, node matches, trace/jobs."""
import io
import os
import threading
import time
import zipfile
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routers import workspace as wr
from app.main import app
from app.schemas.chat import ChatLocation
from app.schemas.security_investigation import InvestigationStatus
from app.schemas.source_graph import SourceGraph, SourceGraphNode
from app.schemas.security import SourceReference
from app.services.investigation_trace import InvestigationRecorder, TraceCallbackHandler
from app.services.project_fix_proposals import ProjectFixProposalService
from app.services.project_workspace import WorkspaceService
from app.services.security_investigation import SecurityInvestigationService
from app.services.source_graph_lookup import match_nodes_at_location

SAMPLE = Path(__file__).resolve().parents[1] / "workspaces" / "orders-api"


class FakeAgent:
    last_truncated = False
    def __init__(self, locations):
        self.locations = locations
    def find_violations(self, details, folder, session_id):
        return self.locations


@pytest.fixture()
def env(tmp_path, monkeypatch):
    import shutil
    root = tmp_path / "ws"; root.mkdir()
    shutil.copytree(SAMPLE, root / "orders-api")
    (root / "orders-api" / ".env").write_text("SECRET=1")
    service = WorkspaceService(root)
    monkeypatch.setattr(wr, "workspace_service", service)
    monkeypatch.setattr(wr, "_last_investigations", {})
    fix = ProjectFixProposalService(service)
    monkeypatch.setattr(wr, "fix_proposal_service", fix)
    # fresh job manager bound to current investigator lookup
    from app.services.investigation_jobs import InvestigationJobManager
    monkeypatch.setattr(wr, "job_manager", InvestigationJobManager(wr._run_job))
    return TestClient(app), service, fix


def _open(client):
    r = client.post("/api/workspace/projects", json={"path": "orders-api"})
    assert r.status_code == 200, r.text
    return r.json()


def _node(nid, ntype, name, start, end, fp="routes/orders.py"):
    return SourceGraphNode(id=nid, type=ntype, name=name, qualified_name=name, file_path=fp,
        source=SourceReference(project_id="p", file_path=fp, module=None, symbol=name, line_start=start, line_end=end, file_hash=None) if start else None)


def test_match_nodes_order():
    graph = SourceGraph(project_id="p", nodes=[
        _node("mod", "module", "orders", None, None),
        _node("cls", "class", "OrderService", 1, 30),
        _node("meth", "method", "get_order", 10, 20),
    ], edges=[])
    matches = match_nodes_at_location(graph, "routes/orders.py", 12)
    assert [m.node_type for m in matches] == ["method", "class", "module"]
    assert [m.node_type for m in match_nodes_at_location(graph, "routes/orders.py", 25)] == ["class", "module"]
    assert match_nodes_at_location(graph, "nope.py", 1) == []


def test_recorder_and_cap():
    rec = InvestigationRecorder()
    with rec.step("planning", "Planning"):
        pass
    assert rec.snapshot()[0].status == "ok"
    copied = rec.snapshot(); copied[0].label = "mutated"
    assert rec.snapshot()[0].label == "Planning"
    with pytest.raises(ValueError):
        with rec.step("model", "Boom"):
            raise ValueError("bad")
    assert rec.snapshot()[-1].status == "failed"
    rec2 = InvestigationRecorder()
    for i in range(210):
        rec2.start("tool", f"s{i}")
    assert len(rec2.snapshot()) <= 201
    assert any("more steps" in s.label for s in rec2.snapshot())


def test_callback_handler():
    rec = InvestigationRecorder()
    handler = TraceCallbackHandler(rec)
    handler.on_tool_start({"name": "lookup"}, "", run_id="r1", inputs={"file_path": "routes/orders.py", "line_number": 12})
    handler.on_tool_end([1, 2], run_id="r1")
    steps = rec.snapshot()
    assert steps[0].kind == "tool" and "routes/orders.py:12" in steps[0].label and steps[0].status == "ok"
    handler.on_tool_start({"name": "lookup"}, "", run_id="r2", inputs={})
    handler.on_tool_error(RuntimeError("nope secret code"), run_id="r2")
    assert rec.snapshot()[-1].status == "failed"


def test_sample_twice_isolated(env, monkeypatch):
    client, service, fix = env
    a, b = _open(client), _open(client)
    assert a["project_id"] != b["project_id"] and a["relative_path"] != b["relative_path"]
    # apply fix in one copy via helper flow
    agent = FakeAgent([ChatLocation(filename="routes/orders.py", linenumber=12)])
    monkeypatch.setattr(wr, "_investigator", SecurityInvestigationService(service, agent=agent))
    pid = a["project_id"]
    body = client.post(f"/api/workspace/projects/{pid}/investigate", json={"rule": {"rule_id": "r", "title": "T", "invariant": "I"}}).json()
    assert body["steps"], "steps included"
    ev = body["findings"][0]["evidence"][0]
    assert ev["node_matches"], "backend node matches filled without hints"
    fid = body["findings"][0]["finding_id"]
    original = (service.root / a["relative_path"] / "routes/orders.py").read_text()
    fixed = original.replace("    return order\n", "    if order.owner_id != customer.customer_id:\n        raise HTTPException(status_code=403, detail='no')\n    return order\n")
    fix.generator = lambda *a_, **k: {"file_path": "routes/orders.py", "proposed_content": fixed, "explanation": "check owner"}
    prop = client.post(f"/api/workspace/projects/{pid}/findings/{fid}/fix-proposals", json={}).json()
    client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/review", json={"decision": "approved", "reviewer": "kenny", "actor": "human"})
    assert client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/apply").status_code == 200
    assert (service.root / "orders-api/routes/orders.py").read_text() == (SAMPLE / "routes/orders.py").read_text()
    assert (service.root / b["relative_path"] / "routes/orders.py").read_text() == original
    # downloads
    assert client.get("/api/workspace/projects/nope/applied-fixes").status_code == 404
    assert client.get("/api/workspace/projects/nope/changes.patch").status_code == 404
    assert client.get("/api/workspace/projects/nope/download").status_code == 404
    patch = client.get(f"/api/workspace/projects/{pid}/changes.patch")
    assert patch.status_code == 200 and "--- a/routes/orders.py" in patch.text and "+++ b/routes/orders.py" in patch.text
    z = client.get(f"/api/workspace/projects/{pid}/download")
    assert z.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert "FORGE_CHANGES.md" in names and "routes/orders.py" in names and ".env" not in names
    assert client.get(f"/api/workspace/projects/{pid}/applied-fixes").json()[0]["applied_at"]
    # rollback clears applied list
    client.post(f"/api/workspace/fix-proposals/{prop['proposal_id']}/rollback")
    assert client.get(f"/api/workspace/projects/{pid}/applied-fixes").json() == []
    assert client.get(f"/api/workspace/projects/{pid}/changes.patch").status_code == 409


def test_hint_dropped_and_dict_hints(env, monkeypatch):
    client, service, fix = env
    pid = _open(client)["project_id"]
    bad = ChatLocation(filename="routes/orders.py", linenumber=12, relatednodes=[{"node_id": "invented", "node_type": "method", "name": "x", "file_path": "routes/orders.py"}])
    agent = FakeAgent([bad])
    monkeypatch.setattr(wr, "_investigator", SecurityInvestigationService(service, agent=agent))
    body = client.post(f"/api/workspace/projects/{pid}/investigate", json={"rule": {"rule_id": "r", "title": "T", "invariant": "I"}}).json()
    ids = [m["node_id"] for m in body["findings"][0]["evidence"][0]["node_matches"]]
    assert "invented" not in ids


def test_mapping_failure_recorded(env, monkeypatch):
    client, service, fix = env
    pid = _open(client)["project_id"]
    agent = FakeAgent([ChatLocation(filename="routes/orders.py", linenumber=12)])
    monkeypatch.setattr(wr, "_investigator", SecurityInvestigationService(service, agent=agent))
    monkeypatch.setattr("app.services.security_investigation.match_nodes_at_location", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    body = client.post(f"/api/workspace/projects/{pid}/investigate", json={"rule": {"rule_id": "r", "title": "T", "invariant": "I"}}).json()
    assert body["findings"][0]["evidence"][0]["status"] == "valid"
    assert any("Graph node mapping failed" in e for e in body["errors"])


def test_jobs_live_cancel_conflict(env, monkeypatch):
    client, service, fix = env
    pid = _open(client)["project_id"]
    event = threading.Event()
    class SlowAgent:
        last_truncated = False
        def find_violations(self, details, folder, session_id, callbacks=None):
            if callbacks:
                callbacks[0].on_tool_start({"name": "lookup"}, "", run_id="x", inputs={"file_path": "routes/orders.py", "line_number": 12})
                callbacks[0].on_tool_end([1], run_id="x")
            event.wait(timeout=5)
            return [ChatLocation(filename="routes/orders.py", linenumber=12)]
    monkeypatch.setattr(wr, "_investigator", SecurityInvestigationService(service, agent=SlowAgent()))
    r = client.post(f"/api/workspace/projects/{pid}/investigations", json={"rule": {"rule_id": "r", "title": "T", "invariant": "I"}})
    assert r.status_code == 202, r.text
    inv_id = r.json()["investigation_id"]
    # second start same IP -> 409 (TestClient host is same)
    r2 = client.post(f"/api/workspace/projects/{pid}/investigations", json={"rule": {"rule_id": "r", "title": "T", "invariant": "I"}})
    assert r2.status_code == 409
    got = client.get(f"/api/workspace/investigations/{inv_id}")
    assert got.json()["status"] == "running" and got.json()["steps"]
    cancelled = client.post(f"/api/workspace/investigations/{inv_id}/cancel")
    event.set()
    for _ in range(50):
        got = client.get(f"/api/workspace/investigations/{inv_id}")
        if got.json()["status"] != "running":
            break
        time.sleep(0.05)
    assert got.json()["status"] in ("cancelled", "completed")
    assert client.get("/api/workspace/investigations/nope").status_code == 404


def test_cleanup_protects_active_and_expires_finished_jobs(tmp_path, monkeypatch):
    from app.api.routers.workspace import _cleanup_old_uploads
    from app.services.investigation_jobs import InvestigationJobManager
    from app.schemas.security_investigation import InvestigationResult

    root = tmp_path / "ws"
    root.mkdir()
    active = root / "active-deadbeef"
    completed = root / "completed-deadbeef"
    failed = root / "failed-deadbeef"
    cancelled = root / "cancelled-deadbeef"
    for project in (active, completed, failed, cancelled):
        project.mkdir()
        (project / "app.py").write_text("x = 1\n")
        old = time.time() - 10 * 3600
        os.utime(project, (old, old))

    active_project = SimpleNamespace(project_id="active", relative_path=active.name)
    finished_projects = {
        "completed": (completed, InvestigationStatus.COMPLETED),
        "failed": (failed, InvestigationStatus.FAILED),
        "cancelled": (cancelled, InvestigationStatus.CANCELLED),
    }
    release = threading.Event()

    def runner(project, *_args):
        if project.project_id == "active":
            release.wait(timeout=5)
        status = finished_projects.get(project.project_id, (None, InvestigationStatus.COMPLETED))[1]
        return InvestigationResult(
            investigation_id=f"investigation-{project.project_id}",
            project_id=project.project_id,
            rule_id="rule",
            status=status,
            summary=status.value,
        )

    manager = InvestigationJobManager(runner)
    manager.start(active_project, None, None, SimpleNamespace(rule_id="rule"), "127.0.0.1")
    for index, (project_id, (path, _status)) in enumerate(finished_projects.items(), start=2):
        manager.start(
            SimpleNamespace(project_id=project_id, relative_path=path.name),
            None,
            None,
            SimpleNamespace(rule_id="rule"),
            f"127.0.0.{index}",
        )
    _cleanup_old_uploads(root, manager)
    assert active.exists()
    release.set()
    for _ in range(50):
        if not manager.active_project_paths(root):
            break
        time.sleep(0.02)
    _cleanup_old_uploads(root, manager)
    assert not active.exists()
    assert not completed.exists() and not failed.exists() and not cancelled.exists()


def test_cleanup_allows_failed_and_cancelled_jobs_after_completion(tmp_path):
    from app.api.routers.workspace import _cleanup_old_uploads
    from app.services.investigation_jobs import InvestigationJobManager
    from app.schemas.security_investigation import InvestigationResult

    root = tmp_path / "ws"
    root.mkdir()
    for name in ("failed-deadbeef", "cancelled-deadbeef"):
        project = root / name
        project.mkdir()
        old = time.time() - 10 * 3600
        os.utime(project, (old, old))

    def runner(project, *_args):
        status = InvestigationStatus.FAILED if project.project_id == "failed" else InvestigationStatus.CANCELLED
        return InvestigationResult(
            investigation_id=f"investigation-{project.project_id}",
            project_id=project.project_id,
            rule_id="rule",
            status=status,
            summary=status.value,
        )

    manager = InvestigationJobManager(runner)
    manager.start(SimpleNamespace(project_id="failed", relative_path="failed-deadbeef"), None, None, SimpleNamespace(rule_id="rule"), "127.0.0.2")
    manager.start(SimpleNamespace(project_id="cancelled", relative_path="cancelled-deadbeef"), None, None, SimpleNamespace(rule_id="rule"), "127.0.0.3")
    for _ in range(50):
        if not manager.active_project_paths(root):
            break
        time.sleep(0.02)
    _cleanup_old_uploads(root, manager)
    assert not (root / "failed-deadbeef").exists()
    assert not (root / "cancelled-deadbeef").exists()


def test_cleanup_ignores_missing_job_state(tmp_path):
    from app.api.routers.workspace import _cleanup_old_uploads
    from app.services.investigation_jobs import InvestigationJobManager

    root = tmp_path / "ws"
    root.mkdir()
    stale = root / "stale-deadbeef"
    stale.mkdir()
    old = time.time() - 10 * 3600
    os.utime(stale, (old, old))
    manager = InvestigationJobManager(lambda *_args: None)
    _cleanup_old_uploads(root, manager)
    assert not stale.exists()
