from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_effective_tenant_ids
from app.core.permissions import READ_TICKETS, require_permissions
from app.database import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.dashboard import DashboardKpis

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

# SLA en riesgo: tickets no cerrados que llevan más de 48h sin resolverse.
# No hay configuración de SLA por tenant todavía; se usa una ventana fija conservadora.
_SLA_WINDOW_HOURS = 48


@router.get("", response_model=DashboardKpis)
def get_dashboard(
    current_user: User = Depends(require_permissions(READ_TICKETS)),
    tenant_ids: list[str] = Depends(get_effective_tenant_ids),
    db: Session = Depends(get_db),
) -> DashboardKpis:
    """KPIs del dashboard con alcance al/los tenant(s) activos del usuario."""
    base = [Ticket.tenant_id.in_(tenant_ids)]
    sla_cutoff = datetime.now(UTC) - timedelta(hours=_SLA_WINDOW_HOURS)

    def count(*filters: object) -> int:
        stmt = select(func.count()).select_from(Ticket).where(*base, *filters)
        return db.scalar(stmt) or 0

    return DashboardKpis(
        ticketsAsignadosAMi=count(Ticket.assignee_id == current_user.id),
        ticketsAbiertos=count(Ticket.status != "closed"),
        ticketsSinAsignar=count(Ticket.assignee_id.is_(None)),
        ticketsSLAEnRiesgo=count(
            Ticket.status.in_(["open", "in_progress", "on_hold"]),
            Ticket.created_at < sla_cutoff,
        ),
    )
