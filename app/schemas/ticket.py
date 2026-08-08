from datetime import datetime

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, pattern="^(low|medium|high|urgent)$")
    language: str = Field(default="es", max_length=10)


class TicketUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|in_progress|on_hold|closed)$")
    priority: str | None = Field(default=None, pattern="^(low|medium|high|urgent)$")
    category: str | None = Field(default=None, max_length=100)
    assignee_id: int | None = None


class TicketMessageIn(BaseModel):
    body: str = Field(min_length=1)


class TicketMessageOut(BaseModel):
    id: int
    ticket_id: int
    author_id: int | None
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketOut(BaseModel):
    id: int
    tenant_id: str
    subject: str
    description: str
    category: str | None
    priority: str | None
    language: str
    status: str
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketSummaryOut(BaseModel):
    id: int
    tenant_id: str
    subject: str
    category: str | None
    priority: str | None
    language: str
    status: str
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketListOut(BaseModel):
    items: list[TicketSummaryOut]
    total: int
    limit: int
    offset: int