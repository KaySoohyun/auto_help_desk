from typing import Literal

from pydantic import BaseModel, Field


class PIIRedactRequest(BaseModel):
    text: str = Field(min_length=1)
    mode: Literal["off", "detect", "redact"] = "redact"


class PIIReportOut(BaseModel):
    types: dict[str, int]
    total: int


class PIIRedactResponse(BaseModel):
    text: str
    report: PIIReportOut