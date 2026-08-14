from datetime import datetime

from pydantic import BaseModel


class CustomerOut(BaseModel):
    id: int
    tenant_id: str
    name: str
    email: str | None
    company: str | None
    plan: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerCreate(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    plan: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None
    plan: str | None = None
