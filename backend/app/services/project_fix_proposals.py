"""AI-assisted, human-approved fix proposals for registered projects.

Separate from the controlled ``security_fixes.py`` demo workflow.
Never executes project code; only ``ast.parse`` validates proposals.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import logging
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.schemas.project_fix import (
    ProjectFixProposal,
    ProposalApplicationStatus,
    ProposalReviewStatus,
)
from app.schemas.security_investigation import InvestigationResult
from app.services.project_workspace import WorkspaceService

logger = logging.getLogger(__name__)

class FixProposalError(Exception):
    status_code = 400


class FixNotFoundError(FixProposalError):
    status_code = 404


class FixConflictError(FixProposalError):
    status_code = 409


class FixNotConfiguredError(FixProposalError):
    status_code = 503


class FixBadResponseError(FixProposalError):
    status_code = 502


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Generator callable: (rule_text, finding, file_path, content, instructions) -> dict
FixGenerator = Callable[..., dict[str, Any]]


def generate_fix_with_muse(rule_text: str, finding: Any, file_path: str, content: str, instructions: str | None) -> dict[str, Any]:
    """Call Meta Model API (Muse) for a full corrected file. No execution."""
    api_key = os.environ.get("META_MODEL_API_KEY", "").strip()
    if not api_key:
        raise FixNotConfiguredError(
            "AI provider is not configured: META_MODEL_API_KEY is not set. "
            "Add your Meta Model API key to backend/.env."
        )
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr

        from app.services.violations_finder_agent import DEFAULT_BASE_URL, DEFAULT_MODEL, _extract_text
    except Exception as error:  # pragma: no cover
        raise FixBadResponseError(f"AI client unavailable: {error}") from error

    model = os.environ.get("META_MODEL_NAME", DEFAULT_MODEL)
    base_url = os.environ.get("META_MODEL_BASE_URL", DEFAULT_BASE_URL)
    client = ChatOpenAI(model=model, base_url=base_url, api_key=SecretStr(api_key), timeout=90.0)
    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "fix_proposal",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "proposed_content": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["file_path", "proposed_content", "explanation"],
                "additionalProperties": False,
            },
        },
    }
    try:
        invoke_client = client.bind(response_format=schema)
    except Exception:
        invoke_client = client
    evidence = "\n".join(
        f"- {item.file_path}:{item.source.line_start if item.source else '?'} {item.excerpt or ''}"
        for item in getattr(finding, "evidence", [])
    )
    prompt = (
        f"Rule:\n{rule_text}\n\nFinding: {finding.title}\n{getattr(finding, 'description', '')}\n"
        f"Evidence:\n{evidence}\n\nUser instructions: {instructions or '(none)'}\n\n"
        f"File: {file_path}\n---\n{content}\n---\n"
        "Return structured JSON {file_path, proposed_content, explanation} with the FULL corrected file. "
        "Make the smallest change that enforces the rule. Do not change unrelated code."
    )
    try:
        try:
            response = invoke_client.invoke([SystemMessage(content="You fix Python security issues. Return only the requested JSON."), HumanMessage(content=prompt)])
        except Exception:
            response = client.invoke([SystemMessage(content="You fix Python security issues. Return only the requested JSON."), HumanMessage(content=prompt)])
    except Exception as error:
        raise FixBadResponseError(f"Model invocation failed: {error}") from error
    text = _extract_text(response.content if response else None).strip()
    data = _parse_json_object(text)
    if data is None:
        logger.warning("Fix proposal: unparseable model response (first 500 chars): %r", text[:500])
        raise FixBadResponseError("Model response was not a valid JSON object.")
    return data


def _parse_json_object(text: str) -> dict[str, Any] | None:
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    candidates = [text]
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict):
            return data
    return None


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").strip().lstrip("./").lstrip("/")


class ProjectFixProposalService:
    def __init__(self, workspace: WorkspaceService, generator: FixGenerator | None = None) -> None:
        self.workspace = workspace
        self.generator = generator or generate_fix_with_muse
        self.proposals: dict[str, ProjectFixProposal] = {}
        self.investigations: dict[str, InvestigationResult] = {}
        self._rollback: dict[str, str] = {}
        self._applied_hash: dict[str, str] = {}

    def record_investigation(self, result: InvestigationResult) -> None:
        self.investigations[result.project_id] = result

    def create_proposal(self, project_id: str, finding_id: str, instructions: str | None = None) -> ProjectFixProposal:
        try:
            self.workspace.get_project(project_id)
        except Exception as error:
            raise FixNotFoundError("Unknown project.") from error
        result = self.investigations.get(project_id)
        finding = None
        if result:
            finding = next((f for f in result.findings if f.finding_id == finding_id), None)
        if finding is None:
            raise FixNotFoundError("Unknown finding for this project.")
        target = None
        for item in finding.evidence:
            if item.status.value == "valid":
                target = item.file_path
                break
        if target is None and finding.affected_files:
            target = finding.affected_files[0]
        if target is None:
            raise FixBadResponseError("Finding has no affected file with valid evidence.")
        try:
            content = self.workspace.read_file(project_id, target)
        except Exception as error:
            raise FixNotFoundError(str(error)) from error
        rule_text = f"{finding.title}\n{finding.description}\n{finding.recommended_remediation}"
        try:
            data = self.generator(rule_text, finding, target, content, instructions)
            proposed, explanation = self._validated_content(data, target, content)
        except FixProposalError as error:
            logger.warning(
                "Fix proposal rejected (project=%s finding=%s file=%s, HTTP %s): %s",
                project_id, finding_id, target, error.status_code, error,
            )
            raise
        diff = "".join(difflib.unified_diff(
            content.splitlines(keepends=True), proposed.splitlines(keepends=True),
            fromfile=target, tofile=target,
        ))
        proposal = ProjectFixProposal(
            proposal_id=f"project-proposal-{uuid.uuid4().hex[:12]}",
            project_id=project_id, finding_id=finding_id, file_path=target,
            expected_source_hash=_digest(content), original_content=content,
            proposed_content=proposed, unified_diff=diff, explanation=str(explanation),
            created_at=_now(),
        )
        self.proposals[proposal.proposal_id] = proposal
        return proposal

    @staticmethod
    def _validated_content(data: Any, target: str, content: str) -> tuple[str, str]:
        if not isinstance(data, dict):
            raise FixBadResponseError("AI fix response was not an object.")
        returned_path = data.get("file_path")
        if isinstance(returned_path, str) and not _normalize_path(target).endswith(_normalize_path(returned_path)) \
                and not _normalize_path(returned_path).endswith(_normalize_path(target)):
            logger.info("Fix proposal: model returned file_path %r; using backend path %r", returned_path, target)
        proposed = data.get("proposed_content")
        if not isinstance(proposed, str) or not proposed.strip():
            raise FixBadResponseError("AI fix returned empty proposed_content.")
        if proposed == content:
            raise FixBadResponseError("AI fix did not change the file.")
        try:
            ast.parse(proposed)
        except SyntaxError as error:
            raise FixBadResponseError(f"AI fix is not valid Python: {error}") from error
        return proposed, str(data.get("explanation") or "")

    def get_proposal(self, proposal_id: str) -> ProjectFixProposal:
        try:
            return self.proposals[proposal_id]
        except KeyError as error:
            raise FixNotFoundError("Unknown fix proposal.") from error

    def review(self, proposal_id: str, decision: str, reviewer: str, actor: str, reason: str | None = None) -> ProjectFixProposal:
        proposal = self.get_proposal(proposal_id)
        if actor != "human":
            raise FixConflictError("An AI actor cannot approve or reject its own proposal.")
        if decision not in ("approved", "rejected"):
            raise FixProposalError("decision must be approved or rejected.")
        if not reviewer or not reviewer.strip():
            raise FixProposalError("A human reviewer is required.")
        if proposal.review_status is not ProposalReviewStatus.PENDING:
            raise FixConflictError("Only pending proposals can receive a review decision.")
        proposal.review_status = ProposalReviewStatus.APPROVED if decision == "approved" else ProposalReviewStatus.REJECTED
        proposal.reviewer = reviewer
        return proposal

    def _target_path(self, proposal: ProjectFixProposal) -> Path:
        root = self.workspace.project_root(proposal.project_id)
        resolved = (root / proposal.file_path).resolve()
        if resolved != root and root not in resolved.parents:
            raise FixConflictError("Proposal target is outside the project root.")
        backend_app = Path(__file__).resolve().parents[1]
        if resolved == backend_app or backend_app in resolved.parents:
            raise FixConflictError("Refusing to write inside backend/app/.")
        return resolved

    def apply(self, proposal_id: str) -> ProjectFixProposal:
        proposal = self.get_proposal(proposal_id)
        if proposal.review_status is not ProposalReviewStatus.APPROVED:
            raise FixConflictError("Only an approved proposal can be applied.")
        if proposal.application_status is ProposalApplicationStatus.APPLIED:
            raise FixConflictError("This proposal has already been applied; use rollback before retrying.")
        target = self._target_path(proposal)
        try:
            current = target.read_bytes().decode("utf-8")
        except OSError as error:
            raise FixNotFoundError(str(error)) from error
        if _digest(current) != proposal.expected_source_hash:
            raise FixConflictError("The file changed since the proposal was created; refusing to apply.")
        self._rollback[proposal_id] = current
        self._atomic_write(target, proposal.proposed_content)
        self._applied_hash[proposal_id] = _digest(proposal.proposed_content)
        proposal.application_status = ProposalApplicationStatus.APPLIED
        proposal.rollback_available = True
        proposal.error = None
        return proposal

    def rollback(self, proposal_id: str) -> ProjectFixProposal:
        proposal = self.get_proposal(proposal_id)
        original = self._rollback.get(proposal_id)
        if not proposal.rollback_available or original is None:
            raise FixConflictError("No rollback is available for this proposal.")
        target = self._target_path(proposal)
        try:
            current = target.read_bytes().decode("utf-8")
        except OSError as error:
            raise FixNotFoundError(str(error)) from error
        if _digest(current) != self._applied_hash.get(proposal_id):
            raise FixConflictError("The file changed after application; refusing rollback.")
        self._atomic_write(target, original)
        proposal.application_status = ProposalApplicationStatus.NOT_APPLIED
        proposal.rollback_available = False
        self._applied_hash.pop(proposal_id, None)
        return proposal

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, target)
