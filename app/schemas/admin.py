from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    tenant_id: str | None = None


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> "UserUpdate":
        if self.role is None and self.is_active is None:
            raise ValueError("Debe indicar role o is_active")
        return self


class TenantPolicyIn(BaseModel):
    ai_enabled: bool = True
    tone: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=10)
    allowed_categories: list[str] | None = None
    escalation_rules: dict | None = None


class TenantPolicyOut(TenantPolicyIn):
    tenant_id: str
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class GlobalPolicyIn(BaseModel):
    llm_model: str | None = None
    ai_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    guardrails_enabled: bool | None = None
    llm_rate_max_calls: int | None = Field(default=None, ge=1)


class GlobalPolicyOut(BaseModel):
    llm_model: str
    ai_confidence_threshold: float
    guardrails_enabled: bool
    llm_rate_max_calls: int
