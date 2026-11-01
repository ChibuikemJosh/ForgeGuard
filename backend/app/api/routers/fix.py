"""Fix endpoint called by the website."""

from fastapi import APIRouter, HTTPException

from app.schemas.fix import FixRequest, FixResult
from app.services.codefixagent import (
    AgentConfigurationError,
    AgentResponseError,
    FixFileError,
)
from app.services.fix import fix_violation_files

router = APIRouter(tags=["fix"])


@router.post("/fix", response_model=list[FixResult])
def fix(request: FixRequest) -> list[FixResult]:
    """Return fixed code for the given files and custom violation."""
    try:
        return fix_violation_files(request.customviolation, request.filenames)
    except FixFileError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except AgentConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except AgentResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
