"""Request and response contracts for the chat endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.source_graph import SourceGraphNodeMatch


class ChatRequest(BaseModel):
    """Website chat input describing a custom security violation."""

    model_config = ConfigDict(extra="forbid")

    custom_security_violation_details: str = Field(min_length=1)
    project_folder: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    project_id: str | None = Field(default=None, min_length=1)


class ChatLocation(BaseModel):
    """A source location relevant to the reported violation."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    line_start: int
    line_end: int
    location_type: Literal["line", "code_block", "function", "class"] = "line"
    symbol_name: str | None = None
    role: Literal["primary", "supporting", "related"] = "supporting"
    relatednodes: list[SourceGraphNodeMatch] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_line_fields(cls, value: Any) -> Any:
        """Normalize legacy single-line fields before extra-field validation."""
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        legacy_fields = ("linenumber", "line_number", "line number")
        legacy_values = [
            normalized.pop(field)
            for field in legacy_fields
            if field in normalized
        ]
        if legacy_values:
            if any(value != legacy_values[0] for value in legacy_values[1:]):
                raise ValueError("Legacy line number fields must agree.")
            legacy_line = legacy_values[0]
            if "line_start" in normalized and normalized["line_start"] != legacy_line:
                raise ValueError("Legacy line number conflicts with line_start.")
            if "line_end" in normalized and normalized["line_end"] != legacy_line:
                raise ValueError("Legacy line number conflicts with line_end.")
            normalized.setdefault("line_start", legacy_line)
            normalized.setdefault("line_end", legacy_line)
        return normalized

    @property
    def linenumber(self) -> int:
        """Return the legacy single-line value for existing callers."""
        return self.line_start
