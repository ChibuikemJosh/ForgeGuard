"""Chat endpoint called by the website."""

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatLocation, ChatRequest
from app.services.chat import find_violation_locations
from app.services.project_workspace import WorkspaceError
from app.services.violations_finder_agent import (
    AgentConfigurationError,
    AgentResponseError,
    ProjectFolderError,
)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=list[ChatLocation])
def chat(request: ChatRequest) -> list[ChatLocation]:
    """Return source locations for a custom security violation report."""
    try:
        return find_violation_locations(
            request.custom_security_violation_details,
            request.project_folder,
            request.session_id,
            request.project_id,
        )
    except ProjectFolderError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except WorkspaceError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except AgentConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except AgentResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
