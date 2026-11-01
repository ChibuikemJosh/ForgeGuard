"""Enrichment tests for ViolationsFinderAgent related-node lookup."""

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from app.services import violations_finder_agent as agent_module
from app.services.project_workspace import WorkspaceError, WorkspaceService
from app.services.violations_finder_agent import ViolationsFinderAgent


def _project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "services").mkdir(parents=True)
    (proj / "services" / "orders.py").write_text(
        "class OrderService:\n"
        "    def get_order(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    (proj / "notes.txt").write_text("hello\n", encoding="utf-8")
    return proj


def _patch_model(monkeypatch: pytest.MonkeyPatch, payload: str) -> None:
    class FakeChatOpenAI:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def bind(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            return AIMessage(content=payload)

    monkeypatch.setattr(agent_module, "ChatOpenAI", FakeChatOpenAI)


def test_find_violations_enriches_python_locations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proj = _project(tmp_path)
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    _patch_model(
        monkeypatch,
        json.dumps(
            {"violations": [{"filename": "services/orders.py", "linenumber": 3}]}
        ),
    )

    agent = ViolationsFinderAgent()
    locations = agent.find_violations("details", str(proj), "session-enrich-1")

    assert len(locations) == 1
    related = locations[0].relatednodes
    assert {node.node_type for node in related} >= {"module", "class", "method"}
    assert {node.file_path for node in related} == {"services/orders.py"}
    assert agent.last_project_id


def test_find_violations_leaves_non_python_without_related_nodes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proj = _project(tmp_path)
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    _patch_model(
        monkeypatch,
        json.dumps({"violations": [{"filename": "notes.txt", "linenumber": 1}]}),
    )

    agent = ViolationsFinderAgent()
    locations = agent.find_violations("details", str(proj), "session-enrich-2")

    assert len(locations) == 1
    assert locations[0].relatednodes == []


def test_find_violations_uses_provided_project_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import app.api.routers.workspace as workspace_router

    root = tmp_path / "ws"
    (root / "proj" / "services").mkdir(parents=True)
    (root / "proj" / "services" / "orders.py").write_text(
        "class OrderService:\n"
        "    def get_order(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    service = WorkspaceService(root)
    reference = service.register_project("proj")
    monkeypatch.setattr(workspace_router, "workspace_service", service)
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    _patch_model(
        monkeypatch,
        json.dumps(
            {"violations": [{"filename": "services/orders.py", "linenumber": 2}]}
        ),
    )

    agent = ViolationsFinderAgent()
    locations = agent.find_violations(
        "details", str(root / "proj"), "session-enrich-3",
        project_id=reference.project_id,
    )

    assert len(locations) == 1
    assert locations[0].relatednodes
    assert agent.last_project_id == reference.project_id


def test_find_violations_unknown_project_id_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import app.api.routers.workspace as workspace_router

    monkeypatch.setattr(
        workspace_router, "workspace_service", WorkspaceService(tmp_path / "ws")
    )
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")

    agent = ViolationsFinderAgent()
    with pytest.raises(WorkspaceError):
        agent.find_violations(
            "details", str(tmp_path), "session-enrich-4",
            project_id="project-nope",
        )
