"""Pure SourceGraph node matching for a file/line location."""
from __future__ import annotations

from app.schemas.source_graph import SourceGraph, SourceGraphNodeMatch

_RANK = {"route": 0, "method": 0, "function": 0, "class": 1, "module": 2, "project": 3}
_PARENT_EDGE_TYPES = {"CONTAINS", "DEFINES", "DEFINES_METHOD", "HANDLES_ROUTE"}


def _span(node) -> int:
    if node.source and node.source.line_start is not None and node.source.line_end is not None:
        return node.source.line_end - node.source.line_start
    return 10**9


def match_nodes_at_location(graph: SourceGraph, file_path: str, line_number: int) -> list[SourceGraphNodeMatch]:
    """Return nodes containing the line, narrowest first. No I/O."""
    parent_by_child: dict[str, str] = {}
    for edge in graph.edges:
        if edge.target and edge.type in _PARENT_EDGE_TYPES:
            parent_by_child[edge.target] = edge.source
    matched = []
    for node in graph.nodes:
        if node.file_path != file_path:
            continue
        if node.type == "module":
            matched.append(node)
            continue
        if node.source is None or node.source.line_start is None or node.source.line_end is None:
            continue
        if node.source.line_start <= line_number <= node.source.line_end:
            matched.append(node)
    matched.sort(key=lambda n: (_RANK.get(n.type, 4), _span(n)))
    return [
        SourceGraphNodeMatch(
            node_id=n.id, node_type=n.type, name=n.name, qualified_name=n.qualified_name,
            file_path=n.file_path,
            start_line=n.source.line_start if n.source else None,
            end_line=n.source.line_end if n.source else None,
            parent_node_id=parent_by_child.get(n.id),
        )
        for n in matched
    ]


class SourceGraphNodeLookup:
    """Validating wrapper used by lookup endpoints/tests."""

    def __init__(self, workspace, indexer=None, resolver=None, builder=None):
        self.workspace = workspace

    def get_nodes_on_path_python(self, project_id: str, file_path: str, line_number: int, graph: SourceGraph) -> list[SourceGraphNodeMatch]:
        self.workspace.get_project(project_id)
        normalized = file_path.replace("\\", "/").strip().lstrip("./").lstrip("/")
        if not normalized or ".." in normalized.split("/"):
            raise ValueError("Invalid file path.")
        content = self.workspace.read_file(project_id, normalized)
        if line_number < 1 or line_number > len(content.splitlines()):
            raise ValueError("Location line number is invalid.")
        return match_nodes_at_location(graph, normalized, line_number)
