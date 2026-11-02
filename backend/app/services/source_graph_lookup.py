"""Lookup SourceGraph nodes associated with validated source locations."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.schemas.source_graph import SourceGraph, SourceGraphNodeMatch
from app.services.project_workspace import WorkspaceError, WorkspaceService
from app.services.python_indexer import PythonIndexer
from app.services.source_graph_builder import SourceGraphBuilder
from app.services.symbol_resolution import SymbolResolver


class SourceGraphLookupError(ValueError):
    """Raised when a SourceGraph lookup cannot be completed safely."""


def match_nodes_at_location(
    graph: SourceGraph,
    file_path: str,
    line_number: int,
) -> list[SourceGraphNodeMatch]:
    """Return graph nodes containing a validated source location.

    The graph is already scoped to one registered project. Matching is based
    only on node source ranges and structural parent edges; caller-provided
    node IDs are never trusted.
    """
    normalized_path = _normalize_path(file_path)
    if not isinstance(line_number, int) or isinstance(line_number, bool) or line_number < 1:
        raise SourceGraphLookupError("line_number must be a positive integer.")

    nodes_by_id = {node.id: node for node in graph.nodes}
    matched_ids = {
        node.id
        for node in graph.nodes
        if node.file_path == normalized_path
        and node.source is not None
        and node.source.line_start is not None
        and node.source.line_end is not None
        and node.source.line_start <= line_number <= node.source.line_end
    }

    parent_by_child: dict[str, str] = {}
    for edge in graph.edges:
        if edge.type in {"DEFINES", "DEFINES_METHOD", "HANDLES_ROUTE"}:
            if edge.target in nodes_by_id and edge.source in nodes_by_id:
                parent_by_child.setdefault(edge.target, edge.source)

    result_ids = set(matched_ids)
    result_ids.update(
        node.id
        for node in graph.nodes
        if node.type == "module" and node.file_path == normalized_path
    )
    for node_id in tuple(matched_ids):
        current = node_id
        while current in parent_by_child:
            parent_id = parent_by_child[current]
            parent = nodes_by_id[parent_id]
            if parent.type == "project":
                break
            if parent.file_path == normalized_path:
                result_ids.add(parent_id)
            current = parent_id

    rank = {"route": 0, "method": 1, "function": 1, "class": 2, "module": 3}
    ordered_nodes = sorted(
        (node for node in graph.nodes if node.id in result_ids),
        key=lambda node: (
            rank.get(node.type, 4),
            (
                (node.source.line_end - node.source.line_start)
                if node.source
                and node.source.line_start is not None
                and node.source.line_end is not None
                else 10**9
            ),
            node.id,
        ),
    )
    return [
        SourceGraphNodeMatch(
            node_id=node.id,
            node_type=node.type,
            name=node.name,
            qualified_name=node.qualified_name,
            file_path=node.file_path,
            start_line=node.source.line_start if node.source else None,
            end_line=node.source.line_end if node.source else None,
            parent_node_id=parent_by_child.get(node.id),
        )
        for node in ordered_nodes
    ]


def _normalize_path(file_path: str) -> str:
    if not isinstance(file_path, str) or not file_path.strip():
        raise SourceGraphLookupError("file_path must be a non-empty string.")
    normalized = file_path.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise SourceGraphLookupError("file_path must stay within the project.")
    return str(path).lstrip("./")


class SourceGraphNodeLookup:
    """Build the existing SourceGraph and match nodes to a source location."""

    def __init__(
        self,
        workspace: WorkspaceService,
        indexer: PythonIndexer | None = None,
        resolver: SymbolResolver | None = None,
        builder: SourceGraphBuilder | None = None,
    ) -> None:
        self.workspace = workspace
        self.indexer = indexer or PythonIndexer()
        self.resolver = resolver or SymbolResolver()
        self.builder = builder or SourceGraphBuilder()

    def get_nodes_on_path_python(
        self,
        project_id: str,
        file_path: str,
        line_number: int,
    ) -> list[SourceGraphNodeMatch]:
        if not isinstance(line_number, int) or isinstance(line_number, bool) or line_number < 1:
            raise SourceGraphLookupError("line_number must be a positive integer.")
        normalized_path = _normalize_path(file_path)
        try:
            project = self.workspace.get_project(project_id)
            index = self.indexer.index_project(self.workspace, project_id)
        except WorkspaceError as error:
            raise SourceGraphLookupError(str(error)) from error
        actual_paths = {path for path in index.files}
        if normalized_path not in actual_paths:
            raise SourceGraphLookupError("Source file does not exist in the project.")
        try:
            content = self.workspace.read_file(project_id, normalized_path)
        except WorkspaceError as error:
            raise SourceGraphLookupError(str(error)) from error
        line_count = len(content.splitlines())
        if line_number > line_count:
            raise SourceGraphLookupError("line_number is outside the source file.")

        graph = self.builder.build(
            project,
            index,
            self.resolver.resolve(index),
        )
        if not any(
            node.file_path == normalized_path
            and node.source is not None
            and node.source.line_start is not None
            and node.source.line_end is not None
            and node.source.line_start <= line_number <= node.source.line_end
            for node in graph.nodes
        ):
            return []
        return match_nodes_at_location(graph, normalized_path, line_number)


def get_nodes_on_path_python(
    project_id: str,
    file_path: str,
    line_number: int,
    workspace: WorkspaceService,
) -> list[SourceGraphNodeMatch]:
    """Return real SourceGraph nodes associated with a Python source location."""
    return SourceGraphNodeLookup(workspace).get_nodes_on_path_python(
        project_id,
        file_path,
        line_number,
    )
