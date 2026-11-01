"""Project workspace and code-index endpoints."""

from __future__ import annotations

import hashlib
import io
import os
import re
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.code_intelligence import CodeIndex
from app.schemas.project_fix import (
    CreateFixProposalRequest,
    FileContentResponse,
    ProjectFixProposal,
    ProjectReviewRequest,
    SampleProject,
)
from app.schemas.security import SecurityRule
from app.schemas.security_investigation import InvestigationResult
from app.schemas.source_graph import SourceGraph
from app.schemas.workspace import ProjectManifest, ProjectReference
from app.services.project_fix_proposals import (
    FixProposalError,
    ProjectFixProposalService,
)
from app.services.project_rules import RULE_PRESETS
from app.services.project_workspace import (
    LANGUAGE_BY_SUFFIX,
    WorkspaceError,
    WorkspaceService,
    _is_sensitive_file,
)
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
fix_proposal_service = ProjectFixProposalService(workspace_service)
_last_investigations: dict[str, InvestigationResult] = {}

SAMPLE_PROJECTS = [
    SampleProject(
        path="orders-api",
        name="Orders API (sample)",
        description="Small FastAPI sample with planted authorization issues and one safe control.",
    )
]

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


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


def _fix_service() -> ProjectFixProposalService:
    # Tests / reconfiguration may swap the module-level workspace service.
    if fix_proposal_service.workspace is not workspace_service:
        fix_proposal_service.workspace = workspace_service
    for pid, result in _last_investigations.items():
        fix_proposal_service.investigations.setdefault(pid, result)
    return fix_proposal_service


@router.get("/samples", response_model=list[SampleProject])
def list_samples() -> list[SampleProject]:
    root = workspace_service.root
    return [s for s in SAMPLE_PROJECTS if (root / s.path).is_dir()]


@router.get("/rules", response_model=list[SecurityRule])
@router.get("/projects/rules", response_model=list[SecurityRule], include_in_schema=False)
def list_rules() -> list[SecurityRule]:
    return RULE_PRESETS


@router.post("/projects/upload", response_model=ProjectReference)
async def upload_project(request: Request, name: str | None = Query(default=None)) -> ProjectReference:
    """Accept a raw .zip body, extract safely inside the workspace root, and register it.

    A future multipart upload can reuse this by producing the same ProjectReference.
    Project code is never executed; files are only read/parsed later.
    """
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Upload exceeds 10 MB limit.")
    filename = request.headers.get("x-file-name", "uploaded-project.zip")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).stem).strip("-.") or "uploaded-project"
    dest_name = f"{stem}-{uuid.uuid4().hex[:8]}"
    root = workspace_service.root
    dest = root / dest_name
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise HTTPException(status_code=400, detail="Upload is not a valid .zip file.") from error
    dest.mkdir(parents=True, exist_ok=False)
    try:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = Path(info.filename).parts
            if Path(info.filename).is_absolute() or ".." in parts:
                raise HTTPException(status_code=400, detail="Zip contains a path outside the project.")
            if any(part in {".git", ".venv", "__pycache__", "node_modules"} for part in parts):
                continue
            if _is_sensitive_file(Path(info.filename).name):
                continue
            if info.file_size > workspace_service.max_file_size_bytes:
                continue
            target = (dest / info.filename).resolve()
            if dest.resolve() not in target.parents:
                raise HTTPException(status_code=400, detail="Zip contains a path outside the project.")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not extract upload: {error}") from error
    # Unwrap a single top-level folder, if present.
    entries = [p for p in dest.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        for child in list(inner.iterdir()):
            child.rename(dest / child.name)
        inner.rmdir()
    try:
        return workspace_service.register_project(dest_name, name or stem)
    except WorkspaceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/projects/{project_id}/files/content", response_model=FileContentResponse)
def get_file_content(project_id: str, path: str = Query(...)) -> FileContentResponse:
    if _is_sensitive_file(Path(path).name):
        raise HTTPException(status_code=400, detail="Sensitive files cannot be read.")
    if not path or Path(path).is_absolute() or ".." in Path(path).parts:
        raise HTTPException(status_code=400, detail="Invalid file path.")
    try:
        workspace_service.get_project(project_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        content = workspace_service.read_file(project_id, path)
    except WorkspaceError as error:
        message = str(error)
        status = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status, detail=message) from error
    return FileContentResponse(
        project_id=project_id, path=path, content=content,
        sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        language=LANGUAGE_BY_SUFFIX.get(Path(path).suffix.lower()),
    )


@router.post("/projects/{project_id}/investigate", response_model=InvestigationResult)
def investigate_project(project_id: str, request: InvestigateRequest) -> InvestigationResult:
    """Investigate a registered project against a security rule."""
    try:
        reference = workspace_service.get_project(project_id)
        index = _indexer.index_project(workspace_service, project_id)
        resolution = SymbolResolver().resolve(index)
        graph = SourceGraphBuilder().build(reference, index, resolution)
        result = _investigator.investigate(reference, index, graph, request.rule, session_id=request.session_id)
        _last_investigations[project_id] = result
        _fix_service().record_investigation(result)
        return result
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/projects/{project_id}/findings/{finding_id}/fix-proposals",
    response_model=ProjectFixProposal,
)
def create_fix_proposal(project_id: str, finding_id: str, request: CreateFixProposalRequest) -> ProjectFixProposal:
    try:
        return _fix_service().create_proposal(project_id, finding_id, request.instructions)
    except FixProposalError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@router.get("/fix-proposals/{proposal_id}", response_model=ProjectFixProposal)
def get_fix_proposal(proposal_id: str) -> ProjectFixProposal:
    try:
        return _fix_service().get_proposal(proposal_id)
    except FixProposalError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@router.post("/fix-proposals/{proposal_id}/review", response_model=ProjectFixProposal)
def review_fix_proposal(proposal_id: str, request: ProjectReviewRequest) -> ProjectFixProposal:
    try:
        return _fix_service().review(proposal_id, request.decision, request.reviewer, request.actor, request.reason)
    except FixProposalError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@router.post("/fix-proposals/{proposal_id}/apply", response_model=ProjectFixProposal)
def apply_fix_proposal(proposal_id: str) -> ProjectFixProposal:
    try:
        return _fix_service().apply(proposal_id)
    except FixProposalError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@router.post("/fix-proposals/{proposal_id}/rollback", response_model=ProjectFixProposal)
def rollback_fix_proposal(proposal_id: str) -> ProjectFixProposal:
    try:
        return _fix_service().rollback(proposal_id)
    except FixProposalError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error
