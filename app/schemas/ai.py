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