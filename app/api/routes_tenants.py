from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_permissions, VIEW_AUDIT
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import TenantOut

router = APIRouter(prefix="/v1/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantOut])
def list_tenants(
    current_user: User = Depends(require_permissions(VIEW_AUDIT)),
    db: Session = Depends(get_db),
) -> list[TenantOut]:
    """Lista todos los tenants. Solo para platform_admin o usuarios con VIEW_AUDIT."""
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    return [TenantOut.model_validate(tenant) for tenant in tenants]


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(
    tenant_id: str,
    current_user: User = Depends(require_permissions(VIEW_AUDIT)),
    db: Session = Depends(get_db),
) -> TenantOut:
    """Obtiene un tenant por ID."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant no encontrado",
        )
    
    return TenantOut.model_validate(tenant)
