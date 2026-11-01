"""Forge Guard security-analysis endpoints for the controlled demo."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.security import (
    AnalysisOutcome,
    AnalysisStatus,
    FixApplicationResponse,
    FixProposal,
    ReviewDecisionRecord,
    ReviewDecisionRequest,
    SecurityAnalysisResponse,
    SecurityGraph,
)
from app.services.security_analysis import (
    ORDER_OWNERSHIP_RULE,
    analyze_demo_state,
)
from app.services.security_fixes import (
    FixWorkflowError,
    apply_fix_proposal,
    build_fix_proposal,
    get_fix_proposal,
    record_review,
    rollback_fix_proposal,
)
from app.services.security_verification import verify_demo

router = APIRouter(prefix="/api/security", tags=["security"])


@router.post("/analyze", response_model=SecurityAnalysisResponse)
def analyze_security_demo(
    corrected: bool = Query(default=False),
    verify: bool = Query(default=True),
) -> SecurityAnalysisResponse:
    """Analyze the controlled vulnerable or corrected demo state."""
    analysis_id = f"analysis-order-ownership-{'corrected' if corrected else 'vulnerable'}"
    try:
        finding, graph = analyze_demo_state(corrected)
    except Exception as error:
        return SecurityAnalysisResponse(
            analysis_id=analysis_id,
            project_id="controlled-fastapi-order-demo",
            status=AnalysisStatus.FAILED,
            outcome=AnalysisOutcome.FAILED,
            rule=ORDER_OWNERSHIP_RULE,
            finding=None,
            graph=SecurityGraph(nodes=[], edges=[]),
            error=f"Analysis failed: {error}",
        )

    fix_proposal = build_fix_proposal(finding)
    verification = None
    if verify:
        target_finding_id = finding.finding_id if finding else "order-ownership-rule"
        verification = verify_demo(corrected, target_finding_id)
        if finding:
            finding.verification_status = verification.status
    if finding is not None:
        outcome = (
            AnalysisOutcome.CONFIRMED
            if verification is None or verification.passed
            else AnalysisOutcome.INCONCLUSIVE
        )
    elif corrected:
        outcome = (
            AnalysisOutcome.SATISFIED
            if verification is None or verification.passed
            else AnalysisOutcome.INCONCLUSIVE
        )
    else:
        outcome = AnalysisOutcome.INCONCLUSIVE
    return SecurityAnalysisResponse(
        analysis_id=analysis_id,
        project_id="controlled-fastapi-order-demo",
        status=AnalysisStatus.COMPLETED,
        outcome=outcome,
        rule=ORDER_OWNERSHIP_RULE,
        finding=finding,
        graph=graph,
        fix_proposal=fix_proposal,
        verification=verification,
    )


@router.get("/rules")
def list_security_rules():
    """Return preset SecurityRule objects for project investigation."""
    from app.services.project_rules import RULE_PRESETS

    return RULE_PRESETS


@router.get("/rules/order-ownership")
def get_order_ownership_rule():
    """Return the stable MVP rule definition."""
    return ORDER_OWNERSHIP_RULE


@router.get("/proposals/{proposal_id}", response_model=FixProposal)
def get_security_fix_proposal(proposal_id: str) -> FixProposal:
    try:
        return get_fix_proposal(proposal_id)
    except FixWorkflowError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/proposals/{proposal_id}/review",
    response_model=ReviewDecisionRecord,
)
def review_security_fix_proposal(
    proposal_id: str,
    request: ReviewDecisionRequest,
) -> ReviewDecisionRecord:
    try:
        return record_review(
            proposal_id=proposal_id,
            decision=request.decision,
            reviewer=request.reviewer,
            actor=request.actor,
            reason=request.reason,
        )
    except FixWorkflowError as error:
        status_code = 404 if "Unknown fix proposal" in str(error) else 409
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.post(
    "/proposals/{proposal_id}/apply",
    response_model=FixApplicationResponse,
)
def apply_security_fix_proposal(proposal_id: str) -> FixApplicationResponse:
    try:
        return apply_fix_proposal(proposal_id)
    except FixWorkflowError as error:
        status_code = 404 if "Unknown fix proposal" in str(error) else 409
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.post(
    "/proposals/{proposal_id}/rollback",
    response_model=FixApplicationResponse,
)
def rollback_security_fix_proposal(proposal_id: str) -> FixApplicationResponse:
    try:
        return rollback_fix_proposal(proposal_id)
    except FixWorkflowError as error:
        status_code = 404 if "Unknown fix proposal" in str(error) else 409
        raise HTTPException(status_code=status_code, detail=str(error)) from error
