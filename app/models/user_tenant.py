from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserTenant(Base):
    """Relación many-to-many entre usuarios y tenants.
    
    Permite que un usuario pertenezca a múltiples tenants con roles diferentes.
    """
    __tablename__ = "user_tenants"
    __table_args__ = (
        Index("ix_user_tenants_user_tenant", "user_id", "tenant_id", unique=True),
        Index("ix_user_tenants_tenant", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(50))  # Rol específico para este tenant
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="tenant_memberships")
    tenant: Mapped["Tenant"] = relationship("Tenant")
