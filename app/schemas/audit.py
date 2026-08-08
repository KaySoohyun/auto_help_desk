from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: int
    created_at: datetime
    tenant_id: str | None
    user_id: int | None
    action: str
    service: str | None
    model: str | None
    model_version: str | None
    prompt_version: str | None
    trace_id: str
    result: str
    confidence: float | None
    detail: dict[str, Any] | None

    model_config = {"from_attributes": True}
