"""Shared business objects for the Forge Guard ownership-analysis workflow."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Severity(str, Enum):
    """Finding severity levels supported by the MVP."""

    HIGH = "high"
    INFO = "info"


class AnalysisStatus(str, Enum):
    """Status of an analysis operation."""

    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisOutcome(str, Enum):
    """Evidence-backed security conclusion for an analysis."""

    CONFIRMED = "confirmed"
    SATISFIED = "satisfied"
    INCONCLUSIVE = "inconclusive"
    FAILED = "failed"


class Confidence(str, Enum):
    """Confidence level for a security finding."""

    HIGH = "high"


class VerificationStatus(str, Enum):
    """Status of security verification for a finding."""

    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"


class ReviewStatus(str, Enum):
    """Human review status for a proposed fix."""

    NOT_PROPOSED = "not_proposed"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApplicationStatus(str, Enum):
    """Application status for a proposed fix."""

    NOT_APPLIED = "not_applied"
    APPLIED = "applied"
    FAILED = "failed"


class ReviewActor(str, Enum):
    """Actor type allowed to record a proposal decision."""

    HUMAN = "human"
    AI = "ai"


class SourceReference(BaseModel):
    """A source location known by the controlled analyzer.

    ``project_id`` and ``module`` are optional so existing callers keep working;
    the Python indexer populates them for source-to-graph provenance.
    """

    model_config = ConfigDict(extra="forbid")

    project_id: str | None = None
    file_path: str
    module: str | None = None
    symbol: str
    line_start: int | None = None
    line_end: int | None = None
    file_hash: str | None = None


class SecurityRule(BaseModel):
    """A rule definition independent of any individual finding."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    title: str | None = None
    invariant: str | None = None
    name: str | None = None
    description: str | None = None
    category: str | None = None
    severity: Severity = Severity.HIGH
    expected_property: str | None = None
    concepts: list[str] = Field(default_factory=list)
    indicators: list[str] = Field(default_factory=list)
    guidance: str | None = None
    examples: list[str] = Field(default_factory=list)


class AnalysisEvidence(BaseModel):
    """Observed facts used to support or clear a security finding."""

    model_config = ConfigDict(extra="forbid")

    authenticated_customer: bool
    retrieves_order: bool
    checks_order_ownership: bool
    ownership_expression: str | None = None
    source: SourceReference
    explanation: str


class SecurityFinding(BaseModel):
    """A potential or confirmed violation of a security rule."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str
    rule_id: str
    severity: Severity
    title: str
    description: str
    affected_route: str
    source: SourceReference
    evidence: AnalysisEvidence
    impact: str
    suggested_remediation: str
    severity_rationale: str
    confidence: Confidence
    confidence_rationale: str
    analysis_status: AnalysisStatus
    verification_status: VerificationStatus = VerificationStatus.NOT_RUN


class SecurityGraphNode(BaseModel):
    """A semantic node for the analyzed security execution path."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    label: str
    source: SourceReference | None = None
    finding_ids: list[str] = Field(default_factory=list)


class SecurityGraphEdge(BaseModel):
    """A directed observed or proposed relationship in the security graph."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    relationship: str
    observed: bool = True
    finding_ids: list[str] = Field(default_factory=list)


class SecurityGraph(BaseModel):
    """Graph data derived from the controlled analysis evidence."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[SecurityGraphNode]
    edges: list[SecurityGraphEdge]


class VerificationResult(BaseModel):
    """An actual verification attempt and its outcome."""

    model_config = ConfigDict(extra="forbid")

    verification_id: str
    finding_id: str
    tested: str
    executed: bool
    passed: bool
    status: VerificationStatus
    summary: str
    error: str | None = None


class FixProposal(BaseModel):
    """A reviewable, not-yet-applied correction proposal."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    finding_id: str
    file_path: str
    unified_diff: str | None = None
    affected_code: str | None = None
    explanation: str
    limitations: str
    expected_source_hash: str | None = None
    verification_status: VerificationStatus = VerificationStatus.NOT_RUN
    verification_output: str | None = None
    rollback_available: bool = False
    review_status: ReviewStatus = ReviewStatus.PENDING
    application_status: ApplicationStatus = ApplicationStatus.NOT_APPLIED


class FixApplicationResponse(BaseModel):
    """Result of applying and verifying a reviewed fix proposal."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    file_path: str
    application_status: ApplicationStatus
    verification_status: VerificationStatus
    verification_command: str
    verification_output: str | None = None
    rollback_available: bool
    error: str | None = None


class SecurityAnalysisResponse(BaseModel):
    """Complete result returned by the MVP analysis endpoint.

    ``error`` carries a human-readable failure reason when ``status`` is
    ``failed``; it is ``None`` for a completed analysis.
    """

    analysis_id: str
    project_id: str
    status: AnalysisStatus
    outcome: AnalysisOutcome
    rule: SecurityRule
    finding: SecurityFinding | None
    graph: SecurityGraph
    fix_proposal: FixProposal | None = None
    verification: VerificationResult | None = None
    error: str | None = None


class ReviewDecision(str, Enum):
    """Human review decision on a proposed fix."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewDecisionRequest(BaseModel):
    """Human review input for a pending fix proposal."""

    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    reviewer: str
    actor: ReviewActor = ReviewActor.HUMAN
    reason: str | None = None


class ReviewDecisionRecord(BaseModel):
    """A recorded human review decision for a fix proposal.

    Kept separate from ``FixProposal`` so the proposal itself remains a
    reviewable artifact while the decision log is append-only.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str
    proposal_id: str
    decision: ReviewDecision
    reviewer: str | None = None
    actor: ReviewActor = ReviewActor.HUMAN
    reason: str | None = None
    decided_at: str | None = None
