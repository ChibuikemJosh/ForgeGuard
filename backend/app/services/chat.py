"""Chat lookup service mapping violation details to source locations."""

from __future__ import annotations

from app.schemas.chat import ChatLocation
from app.services.violations_finder_agent import ViolationsFinderAgent

_agent = ViolationsFinderAgent()


def find_violation_locations(
    custom_security_violation_details: str,
    project_folder: str,
    session_id: str,
    project_id: str | None = None,
) -> list[ChatLocation]:
    """Return source locations via the ViolationsFinderAgent."""
    return _agent.find_violations(
        custom_security_violation_details,
        project_folder,
        session_id,
        project_id=project_id,
    )
