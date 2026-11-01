"""Tests for the SourceGraph related-nodes LangGraph tools."""

from pathlib import Path

from langchain_core.tools import BaseTool

from app.services.project_workspace import WorkspaceService
from app.services.source_graph_tools import (
    PYTHON_TOOL_NAME,
    build_related_nodes_tools,
    detect_language,
    related_nodes_for_location,
    select_tool,
)


def _service(tmp_path: Path) -> tuple[WorkspaceService, str]:
    root = tmp_path / "workspace"
    project = root / "project"
    (project / "services").mkdir(parents=True)
    (project / "services" / "orders.py").write_text(
        "class OrderService:\n"
        "    def get_order(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )
    service = WorkspaceService(root)
    return service, service.register_project("project").project_id


def test_python_tool_is_registered_langgraph_tool(tmp_path: Path) -> None:
    service, project_id = _service(tmp_path)

    tools = build_related_nodes_tools(service, project_id)

    assert set(tools) == {"python"}
    assert isinstance(tools["python"], BaseTool)
    assert tools["python"].name == PYTHON_TOOL_NAME == "get_nodes_on_path_python"


def test_python_tool_returns_matches_for_location(tmp_path: Path) -> None:
    service, project_id = _service(tmp_path)
    tools = build_related_nodes_tools(service, project_id)

    result = tools["python"].invoke(
        {"file_path": "services/orders.py", "line_number": 3}
    )

    assert isinstance(result, list) and result
    assert {item["node_type"] for item in result} >= {"module", "class", "method"}
    assert {item["file_path"] for item in result} == {"services/orders.py"}


def test_select_tool_dispatches_by_language(tmp_path: Path) -> None:
    service, project_id = _service(tmp_path)
    tools = build_related_nodes_tools(service, project_id)

    assert detect_language("services/orders.py") == "python"
    assert select_tool(tools, "services/orders.py") is tools["python"]
    assert select_tool(tools, "notes.txt") is None


def test_unsupported_language_and_missing_file_yield_no_nodes(
    tmp_path: Path,
) -> None:
    service, project_id = _service(tmp_path)
    tools = build_related_nodes_tools(service, project_id)

    assert related_nodes_for_location(tools, "notes.txt", 1) == []
    assert related_nodes_for_location(tools, "services/missing.py", 1) == []
