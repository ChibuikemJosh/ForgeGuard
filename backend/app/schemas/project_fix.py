"""Project (non-demo) AI fix proposal models."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ProposalReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProposalApplicationStatus(str, Enum):
    NOT_APPLIED = "not_applied"
    APPLIED = "applied"
    FAILED = "failed"


class ProjectFixProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    project_id: str
    finding_id: str
    file_path: str
    expected_source_hash: str
    original_content: str
    proposed_content: str
    unified_diff: str
    explanation: str
    review_status: ProposalReviewStatus = ProposalReviewStatus.PENDING
    application_status: ProposalApplicationStatus = ProposalApplicationStatus.NOT_APPLIED
    rollback_available: bool = False
    reviewer: str | None = None
    created_at: str
    error: str | None = None


class CreateFixProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instructions: str | None = None


class ProjectReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str
    reviewer: str
    actor: str = "human"
    reason: str | None = None


class SampleProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    name: str
    description: str


class FileContentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    path: str
    content: str
    sha256: str
    language: str | None = None
