"""Read-only SourceGraph models for observed Python project architecture."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.code_intelligence import CodeIndex
from app.schemas.resolution import ResolutionStatus
from app.schemas.security import SourceReference


class SourceGraphNodeType(str):
    PROJECT = "project"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    ROUTE = "route"


class SourceGraphEdgeType(str):
    CONTAINS = "CONTAINS"
    DEFINES = "DEFINES"
    DEFINES_METHOD = "DEFINES_METHOD"
    IMPORTS = "IMPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    CALLS = "CALLS"
    HANDLES_ROUTE = "HANDLES_ROUTE"


class SourceGraphNode(BaseModel):
    """A node in a read-only SourceGraph."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    name: str
    qualified_name: str | None = None
    module: str | None = None
    file_path: str | None = None
    source: SourceReference | None = None
    file_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceGraphNodeMatch(BaseModel):
    """A SourceGraph node matched to a reported source location."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: str
    name: str
    qualified_name: str | None = None
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    parent_node_id: str | None = None


class SourceGraphEdge(BaseModel):
    """A relationship in a read-only SourceGraph."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str | None = None
    type: str
    status: ResolutionStatus = ResolutionStatus.RESOLVED
    observed: bool = True
    source_ref: SourceReference | None = None
    evidence: str | None = None


class SourceGraphSummary(BaseModel):
    """Statistics calculated from a SourceGraph."""

    model_config = ConfigDict(extra="forbid")

    total_nodes: int = 0
    total_edges: int = 0
    projects: int = 0
    modules: int = 0
    classes: int = 0
    functions: int = 0
    methods: int = 0
    routes: int = 0
    resolved_relationships: int = 0
    ambiguous_relationships: int = 0
    unresolved_relationships: int = 0


class SourceGraph(BaseModel):
    """A read-only representation of an indexed project's architecture."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    project_name: str | None = None
    relative_path: str | None = None
    nodes: list[SourceGraphNode] = Field(default_factory=list)
    edges: list[SourceGraphEdge] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    summary: SourceGraphSummary = Field(default_factory=SourceGraphSummary)
