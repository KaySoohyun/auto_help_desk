import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import REQUEST_AI_SUGGESTION, require_permissions
from app.database import get_db
from app.models.user import User
from app.schemas.pii import PIIRedactRequest, PIIRedactResponse, PIIReportOut
from app.services.audit import AuditService, get_audit_service
from app.services.pii import PiiRedactionError, PiiRedactor

router = APIRouter(prefix="/v1/pii", tags=["pii"])


@router.post("/redact", response_model=PIIRedactResponse)
def redact_text(
    payload: PIIRedactRequest,
    current_user: User = Depends(require_permissions(REQUEST_AI_SUGGESTION)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> PIIRedactResponse:
    """Redacta PII de un texto antes de cualquier uso externo (spec §9.3).

    El texto original nunca se registra: la auditoría solo guarda tipos/conteos.
    """
    redactor = PiiRedactor()
    try:
        result = redactor.redact(payload.text, mode=payload.mode)
    except PiiRedactionError as exc:
        raise HTTPException(status_code=422, detail="Modo inválido") from exc

    audit.log(
        "pii.redacted",
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        service="pii",
        model="PiiRedactor",
        trace_id=str(uuid.uuid4()),
        detail={"mode": payload.mode, "types": result.report.types, "total": result.report.total},
    )

    return PIIRedactResponse(
        text=result.text,
        report=PIIReportOut(types=result.report.types, total=result.report.total),
    )