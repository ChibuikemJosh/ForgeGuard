"""Project workspace and code-index endpoints."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import shutil
import time
import uuid
import zipfile
from pathlib import Path

import difflib

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from app.config import is_production
from app.schemas.code_intelligence import CodeIndex
from app.schemas.project_fix import (
    CreateFixProposalRequest,
    FileContentResponse,
    ProjectFixProposal,
    ProjectReviewRequest,
    ProjectRuleSet,
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
from app.services.generated_rules import generate_rules
from app.services.project_rules import RULE_PRESETS
from app.services.project_workspace import (
    LANGUAGE_BY_SUFFIX,
    PROJECT_MARKER,
    WorkspaceError,
    WorkspaceService,
    _is_sensitive_file,
)
from app.services.python_indexer import PythonIndexer
from app.services.investigation_jobs import InvestigationJobManager, JobConflictError
from app.services.investigation_trace import InvestigationRecorder
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
logger = logging.getLogger(__name__)
_UPLOAD_DIR_RE = re.compile(r"^.+-[0-9a-f]{8}$")
_RATE_LIMIT = 10
_RATE_WINDOW_SECONDS = 3600
_rate_hits: dict[str, list[float]] = {}


def _check_rate_limit(request: Request) -> None:
    if not is_production():
        return
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    hits = [h for h in _rate_hits.get(ip, []) if now - h < _RATE_WINDOW_SECONDS]
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded: at most 10 AI requests per hour in the hosted demo. Please try again later.")
    hits.append(now)
    _rate_hits[ip] = hits


def _cleanup_old_uploads(root: Path) -> None:
    try:
        ttl_hours = float(os.environ.get("FORGE_UPLOAD_TTL_HOURS", "6"))
    except ValueError:
        ttl_hours = 6.0
    cutoff = time.time() - ttl_hours * 3600
    sample_paths = {s.path for s in SAMPLE_PROJECTS}
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    for entry in entries:
        try:
            if not entry.is_dir() or entry.name in sample_paths:
                continue
            if not _UPLOAD_DIR_RE.match(entry.name):
                continue
            if entry.stat().st_mtime >= cutoff:
                continue
            shutil.rmtree(entry)
        except Exception as error:  # never fail the upload
            logger.warning("Could not clean up old upload %s: %s", entry, error)


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
    if is_production() and request.path not in {s.path for s in SAMPLE_PROJECTS}:
        raise HTTPException(status_code=403, detail="Only sample projects can be opened in the hosted demo. Upload a project folder instead.")
    sample = next((s for s in SAMPLE_PROJECTS if s.path == request.path), None)
    if sample is not None:
        root = workspace_service.root
        _cleanup_old_uploads(root)
        copy_name = f"{sample.path}-{uuid.uuid4().hex[:8]}"
        try:
            shutil.copytree(root / sample.path, root / copy_name, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "node_modules", ".DS_Store"))
            (root / copy_name / PROJECT_MARKER).write_text(json.dumps({"source": "sample", "sample_path": sample.path}), encoding="utf-8")
            return workspace_service.register_project(copy_name, request.name or sample.name)
        except WorkspaceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except OSError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    try:
        return workspace_service.register_project(request.path, request.name)
    except WorkspaceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _project_or_404(project_id: str):
    try:
        ref = workspace_service.get_project(project_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        root = workspace_service.project_root(project_id)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail="This project copy has expired. Re-upload the project folder.") from error
    if not root.exists():
        raise HTTPException(status_code=404, detail="This project copy has expired. Re-upload the project folder.")
    return ref


@router.get("/rules", response_model=list[SecurityRule])
@router.get("/projects/rules", response_model=list[SecurityRule], include_in_schema=False)
def list_rules() -> list[SecurityRule]:
    """Preset rules. Frontend uses `/projects/{id}/rules`."""
    return RULE_PRESETS


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


@router.get("/projects/{project_id}/generated-rules", response_model=list[SecurityRule])
def list_generated_rules(project_id: str) -> list[SecurityRule]:
    """Rules derived from this project's own routes/resources (never presets).

    Frontend uses `/projects/{id}/rules`.
    """
    try:
        reference = workspace_service.get_project(project_id)
        index = _indexer.index_project(workspace_service, project_id)
        resolution = _resolver.resolve(index)
        graph = _builder.build(reference, index, resolution)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return generate_rules(graph)


@router.get("/projects/{project_id}/rules", response_model=ProjectRuleSet)
def get_project_rules(project_id: str) -> ProjectRuleSet:
    """The rule set for one project: presets for the sample, generated rules for uploads."""
    _project_or_404(project_id)
    source, _sample_path = workspace_service.project_source(project_id)
    if source == "sample":
        return ProjectRuleSet(project_id=project_id, source=source, rule_origin="preset", rules=RULE_PRESETS, default_rule_id="order-ownership-authorization")
    try:
        reference = workspace_service.get_project(project_id)
        index = _indexer.index_project(workspace_service, project_id)
        resolution = _resolver.resolve(index)
        graph = _builder.build(reference, index, resolution)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    rules = generate_rules(graph)
    return ProjectRuleSet(project_id=project_id, source=source, rule_origin="generated", rules=rules, default_rule_id=rules[0].rule_id if rules else None)


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
    _cleanup_old_uploads(root)
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
            if Path(info.filename).name == ".DS_Store":
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
def investigate_project(project_id: str, request: InvestigateRequest, http_request: Request) -> InvestigationResult:
    """Investigate a registered project against a security rule."""
    _check_rate_limit(http_request)
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


def _run_job(project, index, graph, rule, recorder, investigation_id):
    result = _investigator.investigate(project, index, graph, rule, session_id=investigation_id, recorder=recorder)
    _last_investigations[project.project_id] = result
    _fix_service().record_investigation(result)
    return result


job_manager = InvestigationJobManager(_run_job)


@router.post("/projects/{project_id}/investigations", status_code=202)
def start_investigation(project_id: str, request: InvestigateRequest, http_request: Request):
    _check_rate_limit(http_request)
    try:
        reference = workspace_service.get_project(project_id)
        index = _indexer.index_project(workspace_service, project_id)
        resolution = SymbolResolver().resolve(index)
        graph = SourceGraphBuilder().build(reference, index, resolution)
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    ip = http_request.client.host if http_request.client else "unknown"
    try:
        investigation_id = job_manager.start(reference, index, graph, request.rule, ip)
    except JobConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"investigation_id": investigation_id, "status": "running"}


@router.get("/investigations/{investigation_id}", response_model=InvestigationResult)
def get_investigation(investigation_id: str) -> InvestigationResult:
    result = job_manager.get(investigation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown investigation. The server may have restarted; run the investigation again.")
    return result


@router.post("/investigations/{investigation_id}/cancel", response_model=InvestigationResult)
def cancel_investigation(investigation_id: str) -> InvestigationResult:
    result = job_manager.cancel(investigation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown investigation. The server may have restarted; run the investigation again.")
    return result


@router.get("/projects/{project_id}/applied-fixes", response_model=list[ProjectFixProposal])
def list_applied_fixes(project_id: str) -> list[ProjectFixProposal]:
    _project_or_404(project_id)
    return _fix_service().applied_proposals(project_id)


@router.get("/projects/{project_id}/changes.patch")
def download_patch(project_id: str):
    ref = _project_or_404(project_id)
    service = _fix_service()
    applied = service.applied_proposals(project_id)
    if not applied:
        raise HTTPException(status_code=409, detail="No applied fixes to download.")
    originals = service.original_contents(project_id)
    parts = []
    for path, original in originals.items():
        try:
            current = workspace_service.read_file(project_id, path)
        except WorkspaceError as error:
            raise HTTPException(status_code=404, detail="This project copy has expired. Re-upload the project folder.") from error
        parts.append("".join(difflib.unified_diff(original.splitlines(keepends=True), current.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}")))
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", ref.name).strip("-") or "project"
    return Response(content="".join(parts), media_type="text/x-diff", headers={"Content-Disposition": f'attachment; filename="{name}-forge-fixes.patch"'})


@router.get("/projects/{project_id}/download")
def download_zip(project_id: str):
    ref = _project_or_404(project_id)
    service = _fix_service()
    applied = service.applied_proposals(project_id)
    lines = ["# Forge Guard changes", "", "This is the uploaded copy of your project, excluding .git, virtual environments, node_modules, .env and other sensitive files, and files over 1 MB.", ""]
    if applied:
        lines.append("## Applied fixes")
        for p in applied:
            lines.append(f"- File: {p.file_path} · Finding: {p.finding_id} · Reviewer: {p.reviewer or ''} · Applied: {p.applied_at or ''}")
            lines.append(f"  {p.explanation}")
    else:
        lines.append("No fixes have been applied yet.")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("FORGE_CHANGES.md", "\n".join(lines) + "\n")
        for info in workspace_service.iter_files(project_id):
            if not info.readable:
                continue
            try:
                content = workspace_service.read_file(project_id, info.path)
            except WorkspaceError:
                continue
            zf.writestr(info.path, content)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", ref.name).strip("-") or "project"
    return Response(content=buffer.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{name}-forge.zip"'})


@router.post(
    "/projects/{project_id}/findings/{finding_id}/fix-proposals",
    response_model=ProjectFixProposal,
)
def create_fix_proposal(project_id: str, finding_id: str, request: CreateFixProposalRequest, http_request: Request) -> ProjectFixProposal:
    _check_rate_limit(http_request)
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
