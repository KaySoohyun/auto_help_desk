from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import CONFIGURE_TENANT, require_permissions
from app.database import get_db
from app.models.user import User
from app.repositories.base import TenantScopedRepository
from app.schemas.auth import UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_tenant_users(
    current_user: User = Depends(require_permissions(CONFIGURE_TENANT)),
    db: Session = Depends(get_db),
) -> list[User]:
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol sin tenant asignado",
        )
    repo = TenantScopedRepository(db, User, current_user.tenant_id)
    return list(repo.list())