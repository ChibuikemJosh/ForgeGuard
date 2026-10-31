from __future__ import annotations

from app.schemas.code_intelligence import CodeIndex
from app.schemas.security import SourceReference
from app.schemas.security_investigation import EvidenceItem, EvidenceStatus
from app.schemas.source_graph import SourceGraph
from app.services.project_workspace import WorkspaceService


class EvidenceValidator:
    def __init__(self, workspace, project_id, index, graph):
        self.workspace = workspace
        self.project_id = project_id
        self.index = index
        self.graph = graph
        self.file_hashes = {
            module.file_path: module.file_hash
            for module in index.modules
            if module.file_hash is not None
        }
        self.symbol_ids = {f.id for f in index.functions} | {c.id for c in index.classes}
        self.graph_node_ids = {node.id for node in graph.nodes}
        self.graph_sources = {
            node.id: node.source
            for node in graph.nodes
            if node.source is not None
        }

    def validate(self, item):
        if item.file_path != item.source.file_path:
            return self._invalid(item, "Evidence file path does not match its source reference.")
        if item.source.project_id not in (None, self.project_id):
            return self._invalid(item, "Evidence source belongs to a different project.")
        if item.symbol_id is not None:
            if item.symbol_id not in self.symbol_ids:
                return self._invalid(item, "Evidence symbol does not exist in the index.")
            symbol = next(
                (
                    candidate
                    for candidate in (*self.index.functions, *self.index.classes)
                    if candidate.id == item.symbol_id
                ),
                None,
            )
            if symbol is None or symbol.source.file_path != item.file_path:
                return self._invalid(item, "Evidence symbol does not belong to the evidence file.")
        try:
            content = self.workspace.read_file(self.project_id, item.file_path)
        except Exception as error:
            return self._invalid(item, f"File is not readable: {error}")
        lines = content.splitlines()
        if item.source.line_start is None or item.source.line_end is None:
            return self._invalid(item, "Source line range is required.")
        if (
            item.source.line_start < 1
            or item.source.line_end < item.source.line_start
            or item.source.line_end > len(lines)
        ):
            return self._invalid(item, "Source line range is invalid.")
        if item.excerpt is not None:
            actual = "\n".join(
                lines[item.source.line_start - 1 : item.source.line_end]
            )
            if item.excerpt.strip() != actual.strip():
                return self._invalid(item, "Evidence excerpt does not match source.")
        for node_id in item.related_graph_nodes:
            if node_id not in self.graph_node_ids:
                return self._invalid(item, "Evidence references an unknown graph node.")
            node_source = self.graph_sources.get(node_id)
            if node_source is not None and node_source.file_path != item.file_path:
                return self._invalid(item, "Evidence graph node does not belong to the evidence file.")
        current_hash = self.file_hashes.get(item.file_path)
        if item.file_hash is not None and current_hash is not None and item.file_hash != current_hash:
            updated = item.model_copy(update={"status": EvidenceStatus.STALE})
            updated.validation_error = "Evidence file hash is stale."
            return updated
        updated = item.model_copy(update={"status": EvidenceStatus.VALID})
        updated.validation_error = None
        return updated

    @staticmethod
    def _invalid(item, message):
        updated = item.model_copy(update={"status": EvidenceStatus.INVALID})
        updated.validation_error = message
        return updated
