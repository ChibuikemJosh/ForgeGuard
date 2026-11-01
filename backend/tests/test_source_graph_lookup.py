"""Tests for SourceGraph node lookup by Python source location."""

from pathlib import Path

import pytest

from app.services.project_workspace import WorkspaceService
from app.services.source_graph_lookup import (
    SourceGraphLookupError,
    SourceGraphNodeLookup,
)


def _service(tmp_path: Path) -> tuple[WorkspaceService, str]:
    root = tmp_path / "workspace"
    project = root / "project"
    project.mkdir(parents=True)
    (project / "services").mkdir()
    (project / "services" / "orders.py").write_text(
        "class OrderService:\n"
        "    def get_order(self):\n"
        "        return 1\n"
        "\n"
        "def unrelated():\n"
        "    return 2\n",
        encoding="utf-8",
    )
    (project / "services" / "orders_backup.py").write_text(
        "def get_order():\n"
        "    return 3\n",
        encoding="utf-8",
    )
    service = WorkspaceService(root)
    return service, service.register_project("project").project_id


def test_matches_method_class_and_parent_module_with_real_graph(tmp_path: Path) -> None:
    service, project_id = _service(tmp_path)

    matches = SourceGraphNodeLookup(service).get_nodes_on_path_python(
        project_id,
        r"services\orders.py",
        3,
    )

    types = {match.node_type for match in matches}
    assert {"module", "class", "method"} <= types
    assert all(match.file_path == "services/orders.py" for match in matches)
    assert all(match.node_id for match in matches)
    method = next(match for match in matches if match.node_type == "method")
    assert method.name == "get_order"
    assert method.parent_node_id


def test_does_not_match_similar_filename(tmp_path: Path) -> None:
    service, project_id = _service(tmp_path)

    matches = SourceGraphNodeLookup(service).get_nodes_on_path_python(
        project_id,
        "services/orders.py",
        2,
    )

    assert matches
    assert {match.file_path for match in matches} == {"services/orders.py"}


@pytest.mark.parametrize(
    ("file_path", "line_number"),
    [
        ("services/orders.py", 0),
        ("services/orders.py", -1),
        ("services/missing.py", 1),
        ("../orders.py", 1),
        ("/services/orders.py", 1),
    ],
)
def test_rejects_invalid_lookup_input(
    tmp_path: Path,
    file_path: str,
    line_number: int,
) -> None:
    service, project_id = _service(tmp_path)

    with pytest.raises(SourceGraphLookupError):
        SourceGraphNodeLookup(service).get_nodes_on_path_python(
            project_id,
            file_path,
            line_number,
        )


def test_project_isolation(tmp_path: Path) -> None:
    service, project_id = _service(tmp_path)

    with pytest.raises(SourceGraphLookupError, match="Unknown project"):
        SourceGraphNodeLookup(service).get_nodes_on_path_python(
            "project-does-not-exist",
            "services/orders.py",
            2,
        )
