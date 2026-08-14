from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserTenantBase(BaseModel):
    tenant_id: str
    role: str


class UserTenantCreate(UserTenantBase):
    pass


class UserTenantUpdate(BaseModel):
    role: Optional[str] = None


class UserTenantOut(UserTenantBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserTenantWithDetails(UserTenantOut):
    """Schema con detalles del tenant."""
    tenant_name: Optional[str] = None
    tenant_slug: Optional[str] = None
