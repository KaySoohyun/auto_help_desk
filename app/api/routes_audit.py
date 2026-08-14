from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_effective_tenant_ids
from app.core.permissions import VIEW_AUDIT, require_permissions
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventOut
from app.services.audit import AuditService, get_audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events", response_model=list[AuditEventOut])
def list_audit_events(
    current_user: User = Depends(require_permissions(VIEW_AUDIT)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    action: str | None = Query(default=None),
    service: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    result: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AuditEvent]:
    """Lista eventos de auditoría de los tenants del usuario (append-only), con filtros."""
    filters = [AuditEvent.tenant_id.in_(tenant_ids)]
    if action:
        filters.append(AuditEvent.action == action)
    if service:
        filters.append(AuditEvent.service == service)
    if user_id is not None:
        filters.append(AuditEvent.user_id == user_id)
    if result:
        filters.append(AuditEvent.result == result)
    if date_from:
        filters.append(AuditEvent.created_at >= date_from)
    if date_to:
        filters.append(AuditEvent.created_at <= date_to)

    audit.log(
        "audit.view",
        user_id=current_user.id,
        tenant_id=tenant_ids[0] if tenant_ids else None,
        service="audit",
        result="success",
    )

    stmt = (
        select(AuditEvent)
        .where(*filters)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())
