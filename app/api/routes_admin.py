from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import CONFIGURE_TENANT, MANAGE_AI_POLICIES, require_permissions
from app.database import get_db
from app.models.user import User
from app.schemas.admin import (
    GlobalPolicyIn,
    GlobalPolicyOut,
    TenantPolicyIn,
    TenantPolicyOut,
    UserCreate,
    UserUpdate,
)
from app.schemas.auth import UserOut
from app.services.admin import AdminService, effective_global_policy
from app.services.audit import AuditService, get_audit_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_service(db: Session, current_user: User, audit: AuditService) -> AdminService:
    return AdminService(db, current_user=current_user, audit=audit)


@router.get("/users", response_model=list[UserOut])
def list_tenant_users(
    current_user: User = Depends(require_permissions(CONFIGURE_TENANT)),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[User]:
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol sin tenant asignado",
        )
    stmt = (
        select(User)
        .where(User.tenant_id == current_user.tenant_id)
        .order_by(User.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_permissions(CONFIGURE_TENANT)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> User:
    service = _admin_service(db, current_user, audit)
    return service.create_user(
        email=payload.email,
        password=payload.password,
        role=payload.role,
        tenant_id=payload.tenant_id,
    )


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_permissions(CONFIGURE_TENANT)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> User:
    service = _admin_service(db, current_user, audit)
    return service.update_user(user_id, role=payload.role, is_active=payload.is_active)


@router.get("/ai-policy", response_model=TenantPolicyOut)
def get_tenant_policy(
    current_user: User = Depends(require_permissions(CONFIGURE_TENANT)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> TenantPolicy:
    service = _admin_service(db, current_user, audit)
    return service.get_tenant_policy()


@router.put("/ai-policy", response_model=TenantPolicyOut)
def save_tenant_policy(
    payload: TenantPolicyIn,
    current_user: User = Depends(require_permissions(CONFIGURE_TENANT)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> TenantPolicy:
    service = _admin_service(db, current_user, audit)
    return service.save_tenant_policy(
        ai_enabled=payload.ai_enabled,
        tone=payload.tone,
        language=payload.language,
        allowed_categories=payload.allowed_categories,
        escalation_rules=payload.escalation_rules,
    )


@router.get("/ai-policies/global", response_model=GlobalPolicyOut)
def get_global_policy(
    current_user: User = Depends(require_permissions(MANAGE_AI_POLICIES)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> GlobalPolicyOut:
    service = _admin_service(db, current_user, audit)
    policy = service.get_global_policy()
    return GlobalPolicyOut(**effective_global_policy(policy))


@router.put("/ai-policies/global", response_model=GlobalPolicyOut)
def save_global_policy(
    payload: GlobalPolicyIn,
    current_user: User = Depends(require_permissions(MANAGE_AI_POLICIES)),
    db: Session = Depends(get_db),
    audit: AuditService = Depends(get_audit_service),
) -> GlobalPolicyOut:
    service = _admin_service(db, current_user, audit)
    policy = service.save_global_policy(
        llm_model=payload.llm_model,
        ai_confidence_threshold=payload.ai_confidence_threshold,
        guardrails_enabled=payload.guardrails_enabled,
        llm_rate_max_calls=payload.llm_rate_max_calls,
    )
    return GlobalPolicyOut(**effective_global_policy(policy))
