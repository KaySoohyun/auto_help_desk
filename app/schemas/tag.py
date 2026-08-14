from datetime import datetime

from pydantic import BaseModel


class TagOut(BaseModel):
    id: int
    tenant_id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str


class TicketTagOut(BaseModel):
    ticket_id: int
    tag_id: int
    tag: TagOut

    model_config = {"from_attributes": True}
