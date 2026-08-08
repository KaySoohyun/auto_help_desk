import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.permissions import EDIT_RESPONSE, READ_TICKETS, SEND_RESPONSE, require_permissions
from app.database import get_db
from app.models.user import User
from app.repositories.tickets import MessageView, TicketRepository, TicketSummaryView, TicketView
from app.schemas.ticket import (
    TicketCreate,
    TicketListOut,
    TicketMessageIn,
    TicketMessageOut,
    TicketOut,
    TicketUpdate,
)
from app.services.audit import AuditService, get_audit_service

router = APIRouter(prefix="/v1/tickets", tags=["tickets"])


def _get_trace_id() -> str:
    import uuid as _uuid

    return str(_uuid.uuid4())


def _repo(db: Session, user: User) -> TicketRepository:
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol sin tenant asignado",
        )
    return TicketRepository(db, user.tenant_id)


def _get_or_404(repo: TicketRepository, ticket_id: int):
    """Devuelve el ticket del tenant, o 404 si no existe o es de otro tenant."""
    try:
        ticket = repo.get_or_none(ticket_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado") from exc
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado")
    return ticket


def _audit(
    audit: AuditService,
    user: User,
    action: str,
    model_id: int,
    trace_id: str,
    detail: dict | None = None,
) -> None:
    detail = dict(detail or {})
    detail["ticket_id"] = model_id
    audit.log(
        action,
        user_id=user.id,
        tenant_id=user.tenant_id,
        service="tickets",
        model="Ticket",
        trace_id=trace_id,
        detail=detail,
    )


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    current_user: User = Depends(require_permissions(READ_TICKETS, EDIT_RESPONSE)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> TicketView:
    repo = _repo(db, current_user)
    ticket = repo.create(
        subject=payload.subject,
        description=payload.description,
        category=payload.category,
        priority=payload.priority,
        language=payload.language,
    )
    _audit(audit, current_user, "ticket.created", ticket.id, trace_id)
    return ticket


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(require_permissions(READ_TICKETS)),
    db: Session = Depends(get_db),
) -> TicketView:
    repo = _repo(db, current_user)
    return _get_or_404(repo, ticket_id)


@router.get("", response_model=TicketListOut)
def list_tickets(
    current_user: User = Depends(require_permissions(READ_TICKETS)),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|in_progress|on_hold|closed)$"),
    category: str | None = Query(default=None, max_length=100),
    priority: str | None = Query(default=None, pattern="^(low|medium|high|urgent)$"),
    assignee_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TicketListOut:
    repo = _repo(db, current_user)
    items, total = repo.list(
        status=status_filter,
        category=category,
        priority=priority,
        assignee_id=assignee_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return TicketListOut(items=items, total=total, limit=limit, offset=offset)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    current_user: User = Depends(require_permissions(EDIT_RESPONSE, SEND_RESPONSE)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> TicketView:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sin cambios")
    try:
        ticket = _repo(db, current_user).update(ticket_id, changes)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado") from exc
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado")
    _audit(audit, current_user, "ticket.updated", ticket_id, trace_id, detail=changes)
    return ticket


@router.post("/{ticket_id}/messages", response_model=TicketMessageOut, status_code=status.HTTP_201_CREATED)
def add_message(
    ticket_id: int,
    payload: TicketMessageIn,
    current_user: User = Depends(require_permissions(EDIT_RESPONSE)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> TicketMessageOut:
    repo = _repo(db, current_user)
    _get_or_404(repo, ticket_id)
    message = repo.add_message(ticket_id, current_user.id, payload.body)
    _audit(audit, current_user, "ticket.message", ticket_id, trace_id)
    return TicketMessageOut.model_validate(message)


@router.get("/{ticket_id}/messages", response_model=list[TicketMessageOut])
def list_messages(
    ticket_id: int,
    current_user: User = Depends(require_permissions(READ_TICKETS)),
    db: Session = Depends(get_db),
) -> list[TicketMessageOut]:
    repo = _repo(db, current_user)
    _get_or_404(repo, ticket_id)
    messages = repo.list_messages(ticket_id)
    return [TicketMessageOut.model_validate(m) for m in messages]


@router.post("/{ticket_id}/close", response_model=TicketOut)
def close_ticket(
    ticket_id: int,
    current_user: User = Depends(require_permissions(SEND_RESPONSE)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
    trace_id: str = Depends(_get_trace_id),
) -> TicketView:
    try:
        ticket = _repo(db, current_user).update(ticket_id, {"status": "closed"})
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado") from exc
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado")
    _audit(audit, current_user, "ticket.closed", ticket_id, trace_id)
    return ticket
