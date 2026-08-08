import uuid
from typing import Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit import AuditEvent


class AuditService:
    """Servicio de auditoría append-only (spec §11.3).

    Expone únicamente `log(...)`; no ofrece métodos de actualización ni borrado.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        action: str,
        *,
        user_id: int | None = None,
        tenant_id: str | None = None,
        service: str | None = None,
        model: str | None = None,
        model_version: str | None = None,
        prompt_version: str | None = None,
        trace_id: str | None = None,
        result: str = "success",
        confidence: float | None = None,
        detail: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            service=service,
            model=model,
            model_version=model_version,
            prompt_version=prompt_version,
            trace_id=trace_id or str(uuid.uuid4()),
            result=result,
            confidence=confidence,
            detail=detail,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)
