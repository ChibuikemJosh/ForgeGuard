"""Request and response contracts for the chat endpoint."""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Website chat input describing a custom security violation."""

    model_config = ConfigDict(extra="forbid")

    custom_security_violation_details: str = Field(min_length=1)
    project_folder: str = Field(min_length=1)
    session_id: str = Field(min_length=1)


class ChatLocation(BaseModel):
    """A source location relevant to the reported violation."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    linenumber: int
