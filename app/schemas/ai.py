from pydantic import BaseModel


class ClassificationOut(BaseModel):
    category: str
    subcategory: str | None
    intent: str
    suggested_priority: str
    confidence: float
    rationale: str
    warnings: list[str] = []
    suggestion_id: int
    trace_id: str | None = None


class SummaryOut(BaseModel):
    summary: str
    missing_information: str | None
    confidence: float
    warnings: list[str] = []
    suggestion_id: int
    trace_id: str | None = None


class SuggestedReplyOut(BaseModel):
    suggested_reply: str
    confidence: float
    sources: list[str] = []
    policy_flags: list[str] = []
    warnings: list[str] = []
    suggestion_id: int
    trace_id: str | None = None


class SuggestedReplyRequest(BaseModel):
    tone: str | None = None
    language: str | None = None