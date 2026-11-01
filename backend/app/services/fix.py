"""Fix service generating corrected code for violation reports."""

from __future__ import annotations

from app.schemas.fix import FixResult
from app.services.codefixagent import CodeFixAgent

_agent = CodeFixAgent()


def fix_violation_files(
    customviolation: str,
    filenames: list[str],
) -> list[FixResult]:
    """Return fixed code via the CodeFixAgent."""
    return _agent.fix_violations(customviolation, filenames)
