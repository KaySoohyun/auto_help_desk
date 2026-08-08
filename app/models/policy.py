from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TenantPolicy(Base):
    """Políticas IA de un tenant (spec FR-06).

    Una fila por tenant (`tenant_id` único). Guarda configuración por tenant:
    activación de IA, tono de respuesta, idioma preferido, categorías permitidas
    y reglas de escalamiento. Los valores por defecto los aplica el servicio si
    no existe fila; nunca contiene PII cruda ni secrets.
    """

    __tablename__ = "tenant_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    allowed_categories: Mapped[list | None] = mapped_column(JSON, nullable=True)
    escalation_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class GlobalPolicy(Base):
    """Overrides globales de IA (spec §4.4, permiso `MANAGE_AI_POLICIES`).

    Fila única (id=1). Los campos nulos significan "usar el default de `.env`"
    (`settings`); solo se persisten los que el admin de plataforma define.
    """

    __tablename__ = "global_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_confidence_threshold: Mapped[float | None] = mapped_column(nullable=True)
    guardrails_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    llm_rate_max_calls: Mapped[int | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
