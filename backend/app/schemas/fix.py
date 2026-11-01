"""Request and response contracts for the fix endpoint."""

from pydantic import BaseModel, ConfigDict, Field


class FixRequest(BaseModel):
    """Website fix input: files plus a custom security violation."""

    model_config = ConfigDict(extra="forbid")

    filenames: list[str]
    customviolation: str = Field(min_length=1)


class FixResult(BaseModel):
    """Fixed Python source for one file."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1)
    fixedCode: str = Field(min_length=1)
