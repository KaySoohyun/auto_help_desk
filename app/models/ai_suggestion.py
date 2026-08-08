from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AISuggestion(Base):
    """Sugerencia de IA por ticket (spec §15, FR-09, ADR-003).

    Una única tabla para todos los tipos de sugerencia (classification | summary |
    reply). `output` guarda la salida estructurada SIN PII cruda (el texto de
    entrada nunca se persiste aquí). `state` refleja el ciclo draft → accepted /
    edited / rejected / flagged (feedback en feature 015).
    """

    __tablename__ = "ai_suggestions"
    __table_args__ = (Index("ix_ai_suggestions_tenant_ticket", "tenant_id", "ticket_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # classification | summary | reply
    output: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    state: Mapped[str] = mapped_column(String(20), default="draft")  # draft | accepted | edited | rejected | flagged
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )