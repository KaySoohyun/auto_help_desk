from pydantic import BaseModel


class KbRecommendation(BaseModel):
    article_id: int
    title: str
    score: float


class PiiDetection(BaseModel):
    type: str
    value: str
    position: int


class AnalyzeOut(BaseModel):
    classification: dict
    summary: dict
    suggested_reply: dict
    kb_recommendations: list[KbRecommendation] = []
    pii_detected: list[PiiDetection] = []
    risks: list[str] = []
