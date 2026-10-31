from pathlib import Path

from app.schemas.chat import ChatLocation
from app.schemas.security import SecurityRule
from app.services.project_workspace import WorkspaceService
from app.services.python_indexer import PythonIndexer
from app.services.security_investigation import SecurityInvestigationService
from app.services.source_graph_builder import SourceGraphBuilder
from app.services.symbol_resolution import SymbolResolver


def _workspace(tmp_path, files):
    root = tmp_path / "workspace"
    root.mkdir(exist_ok=True)
    project = root / "proj"
    project.mkdir(exist_ok=True)
    for rel, content in files.items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    service = WorkspaceService(root)
    ref = service.register_project("proj")
    return service, ref


def _index_graph(service, ref):
    index = PythonIndexer().index_project(service, ref.project_id)
    resolution = SymbolResolver().resolve(index)
    graph = SourceGraphBuilder().build(ref, index, resolution)
    return index, graph


class FakeAgent:
    def __init__(self, locations):
        self.locations = locations

    def find_violations(self, details, project_folder, session_id):
        return self.locations


def test_investigation_with_valid_agent_location(tmp_path):
    service, ref = _workspace(tmp_path, {"m.py": "def foo():\n    return 1\n"})
    index, graph = _index_graph(service, ref)
    rule = SecurityRule(rule_id="test-rule", title="Test rule", invariant="Something must be true.")
    agent = FakeAgent([ChatLocation(filename="m.py", linenumber=1)])
    investigator = SecurityInvestigationService(service, agent=agent)
    result = investigator.investigate(ref, index, graph, rule)
    assert result.status.value == "completed"
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.status.value == "potential"
    assert finding.evidence[0].status.value == "valid"
    assert finding.evidence[0].file_path == "m.py"
    assert finding.affected_files == ["m.py"]


def test_investigation_with_no_locations_is_inconclusive(tmp_path):
    service, ref = _workspace(tmp_path, {"m.py": "def foo():\n    pass\n"})
    index, graph = _index_graph(service, ref)
    rule = SecurityRule(rule_id="r", title="R", invariant="I")
    investigator = SecurityInvestigationService(service, agent=FakeAgent([]))
    result = investigator.investigate(ref, index, graph, rule)
    assert result.status.value == "inconclusive"
    assert result.findings == []


def test_investigation_with_invalid_location_is_inconclusive(tmp_path):
    service, ref = _workspace(tmp_path, {"m.py": "def foo():\n    pass\n"})
    index, graph = _index_graph(service, ref)
    rule = SecurityRule(rule_id="r", title="R", invariant="I")
    investigator = SecurityInvestigationService(service, agent=FakeAgent([ChatLocation(filename="m.py", linenumber=99)]))
    result = investigator.investigate(ref, index, graph, rule)
    assert result.status.value == "inconclusive"
    assert result.findings[0].status.value == "inconclusive"
    assert result.errors


def test_provider_unavailable_returns_failed(tmp_path):
    from app.services.violations_finder_agent import AgentConfigurationError

    class FailingAgent:
        def find_violations(self, *args, **kwargs):
            raise AgentConfigurationError("META_MODEL_API_KEY is not set.")

    service, ref = _workspace(tmp_path, {"m.py": "def foo():\n    pass\n"})
    index, graph = _index_graph(service, ref)
    rule = SecurityRule(rule_id="r", title="R", invariant="I")
    investigator = SecurityInvestigationService(service, agent=FailingAgent())
    result = investigator.investigate(ref, index, graph, rule)
    assert result.status.value == "failed"
    assert "META_MODEL_API_KEY" in result.errors[0]


def test_evidence_validator_stale_hash(tmp_path):
    from app.schemas.security_investigation import EvidenceItem, EvidenceType
    from app.services.evidence_validation import EvidenceValidator

    service, ref = _workspace(tmp_path, {"m.py": "def foo():\n    pass\n"})
    index, graph = _index_graph(service, ref)
    validator = EvidenceValidator(service, ref.project_id, index, graph)
    source = next(n for n in graph.nodes if n.type == "function").source
    item = EvidenceItem(
        evidence_id="e1",
        evidence_type=EvidenceType.SOURCE_EXCERPT,
        description="test",
        file_path="m.py",
        source=source,
        excerpt="def foo():\n    pass",
        file_hash="stale-hash",
    )
    validated = validator.validate(item)
    assert validated.status.value == "stale"


def test_evidence_validator_inconsistent_excerpt(tmp_path):
    from app.schemas.security_investigation import EvidenceItem, EvidenceType
    from app.services.evidence_validation import EvidenceValidator

    service, ref = _workspace(tmp_path, {"m.py": "def foo():\n    pass\n"})
    index, graph = _index_graph(service, ref)
    validator = EvidenceValidator(service, ref.project_id, index, graph)
    source = next(n for n in graph.nodes if n.type == "function").source
    item = EvidenceItem(
        evidence_id="e1",
        evidence_type=EvidenceType.SOURCE_EXCERPT,
        description="test",
        file_path="m.py",
        source=source,
        excerpt="def bar():",
    )
    validated = validator.validate(item)
    assert validated.status.value == "invalid"
    assert "excerpt" in (validated.validation_error or "")


def test_evidence_validator_rejects_mismatched_source_reference(tmp_path):
    from app.schemas.security_investigation import EvidenceItem, EvidenceType
    from app.services.evidence_validation import EvidenceValidator

    service, ref = _workspace(tmp_path, {"m.py": "def foo():\n    pass\n"})
    index, graph = _index_graph(service, ref)
    validator = EvidenceValidator(service, ref.project_id, index, graph)
    item = EvidenceItem(
        evidence_id="e1",
        evidence_type=EvidenceType.SOURCE_EXCERPT,
        description="test",
        file_path="m.py",
        source={
            "project_id": ref.project_id,
            "file_path": "other.py",
            "symbol": "m.py",
            "line_start": 1,
            "line_end": 1,
        },
        excerpt="def foo():",
    )

    validated = validator.validate(item)

    assert validated.status.value == "invalid"
    assert "file path" in (validated.validation_error or "")


def test_investigation_maps_class_locations_to_graph_nodes(tmp_path):
    service, ref = _workspace(
        tmp_path,
        {"m.py": "class Handler:\n    pass\n"},
    )
    index, graph = _index_graph(service, ref)
    rule = SecurityRule(rule_id="r", title="R", invariant="I")
    investigator = SecurityInvestigationService(
        service,
        agent=FakeAgent([ChatLocation(filename="m.py", linenumber=1)]),
    )

    result = investigator.investigate(ref, index, graph, rule)

    class_id = index.classes[0].id
    assert result.findings[0].affected_symbols == [class_id]
    assert result.findings[0].related_graph_nodes == [class_id]


def test_investigate_endpoint(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.api.routers import workspace as workspace_router
    from app.main import app
    from app.schemas.security import SecurityRule

    root = tmp_path / "workspace"
    root.mkdir(exist_ok=True)
    project = root / "proj"
    project.mkdir(exist_ok=True)
    (project / "m.py").write_text("def foo():\n    pass\n", encoding="utf-8", newline="\n")
    service = WorkspaceService(root)
    ref = service.register_project("proj")
    monkeypatch.setattr(workspace_router, "workspace_service", service)
    monkeypatch.setattr(
        workspace_router,
        "_investigator",
        SecurityInvestigationService(service, agent=FakeAgent([ChatLocation(filename="m.py", linenumber=1)])),
    )
    client = TestClient(app)
    response = client.post(
        f"/api/workspace/projects/{ref.project_id}/investigate",
        json={
            "rule": {
                "rule_id": "r",
                "title": "R",
                "invariant": "I",
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["findings"][0]["status"] == "potential"
