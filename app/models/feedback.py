from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Feedback(Base):
    """Feedback del agente sobre una sugerencia de IA (spec §15.4, CU-04, FR-09).

    Un feedback por sugerencia (`suggestion_id` único). `action` refleja la
    decisión del agente (accepted | edited | rejected | flagged). `reason` y
    `edited_content_hash` son opcionales y nunca se envían al LLM ni se
    registran en auditoría (solo el action y la sugerencia).
    """

    __tablename__ = "feedback"
    __table_args__ = (Index("ix_feedback_tenant_suggestion", "tenant_id", "suggestion_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    suggestion_id: Mapped[int] = mapped_column(
        ForeignKey("ai_suggestions.id", ondelete="CASCADE"), unique=True, index=True
    )
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(20))  # accepted | edited | rejected | flagged
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
