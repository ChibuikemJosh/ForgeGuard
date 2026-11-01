"""Project workspace and code-index endpoints."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.code_intelligence import CodeIndex
from app.schemas.security import SecurityRule
from app.schemas.security_investigation import InvestigationResult
from app.schemas.source_graph import SourceGraph
from app.schemas.workspace import ProjectManifest, ProjectReference
from app.services.project_workspace import WorkspaceError, WorkspaceService
from app.services.python_indexer import PythonIndexer
from app.services.security_investigation import SecurityInvestigationService
from app.services.source_graph_builder import SourceGraphBuilder
from app.services.symbol_resolution import SymbolResolver


def _default_root() -> Path:
    configured = os.environ.get("FORGE_WORKSPACE_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path.cwd() / "workspaces"


workspace_service = WorkspaceService(_default_root())
_indexer = PythonIndexer()
_investigator = SecurityInvestigationService(workspace_service)
_resolver = SymbolResolver()
_builder = SourceGraphBuilder()


class OpenProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = "."
    name: str | None = None


router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class InvestigateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: SecurityRule
    session_id: str | None = None



@router.post("/projects", response_model=ProjectReference)
def open_project(request: OpenProjectRequest) -> ProjectReference:
    """Register an existing directory inside the configured workspace root."""
    try:
        return workspace_service.register_project(request.path, request.name)
    except WorkspaceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/projects/{project_id}", response_model=ProjectReference)
def get_project(project_id: str) -> ProjectReference:
    try:
        return workspace_service.get_project(project_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/projects/{project_id}/manifest", response_model=ProjectManifest
)
def get_manifest(project_id: str) -> ProjectManifest:
    try:
        return workspace_service.manifest(project_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/projects/{project_id}/files")
def list_files(project_id: str) -> dict:
    try:
        files = workspace_service.iter_files(project_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"project_id": project_id, "files": [f.model_dump() for f in files]}


@router.get("/projects/{project_id}/index", response_model=CodeIndex)
def get_index(project_id: str) -> CodeIndex:
    try:
        workspace_service.get_project(project_id)
        return _indexer.index_project(workspace_service, project_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/projects/{project_id}/source-graph", response_model=SourceGraph
)
def get_source_graph(project_id: str) -> SourceGraph:
    """Build and return a read-only SourceGraph for a registered project."""
    try:
        reference = workspace_service.get_project(project_id)
        index = _indexer.index_project(workspace_service, project_id)
        resolution = _resolver.resolve(index)
        return _builder.build(reference, index, resolution)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/projects/{project_id}/investigate", response_model=InvestigationResult)
def investigate_project(project_id: str, request: InvestigateRequest) -> InvestigationResult:
    """Investigate a registered project against a security rule."""
    try:
        reference = workspace_service.get_project(project_id)
        index = _indexer.index_project(workspace_service, project_id)
        from app.services.symbol_resolution import SymbolResolver
        from app.services.source_graph_builder import SourceGraphBuilder
        resolution = SymbolResolver().resolve(index)
        graph = SourceGraphBuilder().build(reference, index, resolution)
        return _investigator.investigate(reference, index, graph, request.rule, session_id=request.session_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
