"""Models for general, evidence-gated security investigation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.security import Severity, SourceReference, VerificationStatus


class EvidenceType(str, Enum):
    OBSERVED_FACT = "observed_fact"
    SOURCE_EXCERPT = "source_excerpt"
    GRAPH_RELATIONSHIP = "graph_relationship"
    SYMBOL_REFERENCE = "symbol_reference"
    FILE_HASH = "file_hash"
    AI_INTERPRETATION = "ai_interpretation"


class EvidenceStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"
    INCONSISTENT = "inconsistent"


class InvestigationStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class FindingStatus(str, Enum):
    POTENTIAL = "potential"
    VALIDATED = "validated"
    INCONCLUSIVE = "inconclusive"
    UNSUPPORTED = "unsupported"


class EvidenceItem(BaseModel):
    """A piece of evidence supporting or refuting a finding."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    evidence_type: EvidenceType
    description: str
    file_path: str
    source: SourceReference
    excerpt: str | None = None
    symbol_id: str | None = None
    file_hash: str | None = None
    observed: bool = False
    related_graph_nodes: list[str] = Field(default_factory=list)
    status: EvidenceStatus = EvidenceStatus.VALID
    validation_error: str | None = None


class InvestigationFinding(BaseModel):
    """A structured, evidence-gated security finding."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    rule_id: str
    title: str
    description: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    status: FindingStatus
    affected_files: list[str] = Field(default_factory=list)
    affected_symbols: list[str] = Field(default_factory=list)
    related_graph_nodes: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    reasoning: str
    recommended_remediation: str
    verification_status: VerificationStatus = VerificationStatus.NOT_RUN


class InvestigationResult(BaseModel):
    """Result of investigating a project against a security rule."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    project_id: str
    rule_id: str
    status: InvestigationStatus
    findings: list[InvestigationFinding] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    summary: str = ""
