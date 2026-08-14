from pydantic import BaseModel


class DashboardKpis(BaseModel):
    """KPIs del dashboard por tenant(s) activos del usuario."""

    ticketsAsignadosAMi: int
    ticketsAbiertos: int
    ticketsSinAsignar: int
    ticketsSLAEnRiesgo: int
