from datetime import datetime

from pydantic import BaseModel


class TenantOut(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantCreate(BaseModel):
    id: str
    name: str
    slug: str
