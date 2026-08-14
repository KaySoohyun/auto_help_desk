from datetime import datetime

from pydantic import BaseModel, Field


class KbCategoryOut(BaseModel):
    id: int
    tenant_id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class KbCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
