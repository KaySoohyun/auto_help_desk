from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_tenant import UserTenant


class UserTenantRepository:
    """Repositorio para operaciones con UserTenant."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_user_and_tenant(self, user_id: int, tenant_id: str) -> Optional[UserTenant]:
        """Obtiene la membresía de un usuario en un tenant específico."""
        stmt = select(UserTenant).where(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_user_tenants(self, user_id: int) -> list[UserTenant]:
        """Obtiene todas las membresías de un usuario."""
        stmt = select(UserTenant).where(UserTenant.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_tenant_users(self, tenant_id: str) -> list[UserTenant]:
        """Obtiene todos los usuarios de un tenant."""
        stmt = select(UserTenant).where(UserTenant.tenant_id == tenant_id)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, user_id: int, tenant_id: str, role: str) -> UserTenant:
        """Crea una nueva membresía de usuario en un tenant."""
        user_tenant = UserTenant(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role
        )
        self.db.add(user_tenant)
        self.db.commit()
        self.db.refresh(user_tenant)
        return user_tenant

    def update_role(self, user_id: int, tenant_id: str, role: str) -> Optional[UserTenant]:
        """Actualiza el rol de un usuario en un tenant."""
        user_tenant = self.get_by_user_and_tenant(user_id, tenant_id)
        if user_tenant:
            user_tenant.role = role
            self.db.commit()
            self.db.refresh(user_tenant)
        return user_tenant

    def delete(self, user_id: int, tenant_id: str) -> bool:
        """Elimina la membresía de un usuario en un tenant."""
        user_tenant = self.get_by_user_and_tenant(user_id, tenant_id)
        if user_tenant:
            self.db.delete(user_tenant)
            self.db.commit()
            return True
        return False

    def user_has_tenant(self, user_id: int, tenant_id: str) -> bool:
        """Verifica si un usuario es miembro de un tenant."""
        return self.get_by_user_and_tenant(user_id, tenant_id) is not None

    def get_user_role_in_tenant(self, user_id: int, tenant_id: str) -> Optional[str]:
        """Obtiene el rol de un usuario en un tenant específico."""
        user_tenant = self.get_by_user_and_tenant(user_id, tenant_id)
        return user_tenant.role if user_tenant else None
